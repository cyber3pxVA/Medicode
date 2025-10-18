from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from app import get_nlp
from app.utils.audit import log_audit_trail
from .forms import ClinicalNoteForm
from app.models.db import ExtractedCode, db
from . import main
import re
import os

# DRG provider abstraction (isolated; optional)
try:
    from app.drg.provider import drg_enabled, enrich_codes_with_drgs
except Exception:  # If provider missing, define safe fallbacks
    def drg_enabled():
        return False
    def enrich_codes_with_drgs(_codes):
        for _c in _codes:
            _c['drg_codes'] = []

@main.route('/extract', methods=['POST'])
def extract_codes_route():
    clinical_text = request.json.get('clinical_text')
    if not clinical_text:
        return jsonify({'error': 'No clinical text provided'}), 400

    # Fallback: extract explicit ICD-10 looking tokens from raw text (e.g., E11, J18.9, N18.3)
    # Pattern captures: single letter + 2 digits (optionally a third), optional dot + 1-4 alphanum
    # Avoid matching inside longer alphanumerics by using word boundaries.
    icd_pattern = re.compile(r'\b([A-TV-Z][0-9]{2}[0-9]?(?:\.[0-9A-Z]{1,4})?)\b', re.IGNORECASE)
    explicit_icd_tokens = set(m.upper() for m in icd_pattern.findall(clinical_text))

    # Use RAG-enhanced pipeline if available, fallback to base pipeline
    use_rag = False
    try:
        import os
        use_rag = os.environ.get('USE_RAG', '0') == '1'
    except Exception:
        pass
    suppressed_negated = []
    try:
        umls_path = current_app.config.get('UMLS_PATH', 'umls_data')
        if use_rag:
            from app.nlp.rag_pipeline import get_rag_pipeline
            nlp_pipeline = get_rag_pipeline(umls_path)
            codes = nlp_pipeline.process_text(clinical_text)
        else:
            base_pipeline = get_nlp()
            codes = base_pipeline.process_text(clinical_text)
            suppressed_negated = getattr(base_pipeline, 'last_suppressed_negated', []) or []
        if use_rag and not codes:
            print("DEBUG: RAG pipeline returned 0 codes in /extract, falling back to base pipeline")
            base_pipeline = get_nlp()
            codes = base_pipeline.process_text(clinical_text)
            suppressed_negated = getattr(base_pipeline, 'last_suppressed_negated', []) or []
        # Normalize CUIs (canonical mapping) before enrichment/backfill
        try:
            from app.utils.cui_normalization import get_canonical_cui
            for c in codes:
                canon = get_canonical_cui(c.get('cui'))
                if canon and canon != c.get('cui'):
                    c['original_cui'] = c['cui']
                    c['cui'] = canon
        except Exception:
            pass
        # Backfill ICD-10 / SNOMED codes if RAG left them empty
        try:
            from app.utils.umls_lookup import get_codes_for_cui as _lookup_codes
            for c in codes:
                if (not c.get('icd10_codes')) or (not c.get('snomed_codes')):
                    extra = _lookup_codes(c['cui'], umls_path)
                    if not c.get('icd10_codes'):
                        c['icd10_codes'] = extra.get('icd10_codes', [])
                    if not c.get('snomed_codes'):
                        c['snomed_codes'] = extra.get('snomed_codes', [])
        except Exception:
            pass
    except Exception as e:
        # Fallback to base pipeline
        nlp_pipeline = get_nlp()
        codes = nlp_pipeline.process_text(clinical_text)
        from app.utils.umls_lookup import get_codes_for_cui
        umls_path = current_app.config.get('UMLS_PATH', 'umls_data')
        for c in codes:
            extra_codes = get_codes_for_cui(c['cui'], umls_path)
            c['snomed_codes'] = extra_codes.get('snomed_codes', [])
            c['icd10_codes'] = extra_codes.get('icd10_codes', [])

    # DRG enrichment always OFF in API unless explicitly flagged via query param (?inpatient=1)
    inpatient_flag = request.args.get('inpatient') == '1'
    # If pipeline/backfill produced no ICD-10 codes but we see explicit tokens, inject stub concepts
    if explicit_icd_tokens:
        seen_codes = { (entry.get('code') if isinstance(entry, dict) else None)
                       for c in codes for entry in (c.get('icd10_codes') or []) }
        missing_tokens = [tok for tok in explicit_icd_tokens if tok not in seen_codes]
        if missing_tokens:
            for mt in missing_tokens:
                codes.append({
                    'cui': f'AUTO_ICD_{mt}',
                    'term': mt,
                    'similarity': 1.0,
                    'semtypes': [],
                    'icd10_codes': [{'code': mt, 'desc': 'Explicit mention (regex fallback)'}],
                    'snomed_codes': [],
                })
    drg_rationale = None
    
    # DRG enrichment (heuristic method for inpatient)
    if inpatient_flag and drg_enabled():
        print("DEBUG: Using traditional heuristic DRG method")
        enrich_codes_with_drgs(codes)
        # Severity selection + rationale (heuristic)
        try:
            from app.drg.severity import apply_drg_severity_selection
            drg_rationale = apply_drg_severity_selection(codes)
            if drg_rationale:
                drg_rationale['method'] = 'Heuristic Analysis'
        except Exception as _e:
            drg_rationale = None
    else:
        # Outpatient - clear DRG codes
        for c in codes:
            c['drg_codes'] = []

    log_audit_trail(clinical_text, codes)
    return jsonify({
        'codes': codes, 
        'suppressed_negated': suppressed_negated, 
        'drg_rationale': drg_rationale, 
        'features': {
            'USE_RAG': use_rag,
            'ENABLE_DRG': drg_enabled(),
            'ENABLE_OPENAI_DRG': os.environ.get('ENABLE_OPENAI_DRG', '0') == '1',
        }
    })

@main.route('/ai-analyze', methods=['POST'])
def ai_analyze_codes():
    """
    Second step: AI analysis of NLP-extracted codes
    This endpoint takes the results from /extract and performs OpenAI GPT-4o analysis
    """
    data = request.json
    clinical_text = data.get('clinical_text', '')
    codes = data.get('codes', [])
    
    if not clinical_text or not codes:
        return jsonify({'error': 'Clinical text and codes are required'}), 400
    
    # Check if OpenAI is enabled
    use_openai_drg = os.environ.get('ENABLE_OPENAI_DRG', '0') == '1'
    if not use_openai_drg:
        return jsonify({
            'error': 'OpenAI DRG analysis is not enabled',
            'message': 'Set ENABLE_OPENAI_DRG=1 and provide OPENAI_API_KEY to use AI analysis'
        }), 400
    
    try:
        from app.ai.openai_drg_analyzer import analyze_concepts_with_openai
        
        # Extract patient demographics if available from text
        patient_info = {}
        age_match = re.search(r'(\d+)[-\s]?year[-\s]?old', clinical_text, re.IGNORECASE)
        if age_match:
            patient_info['age'] = age_match.group(1)
        
        gender_match = re.search(r'\b(male|female|man|woman)\b', clinical_text, re.IGNORECASE)
        if gender_match:
            patient_info['gender'] = gender_match.group(1)
        
        print(f"DEBUG: Starting AI analysis for {len(codes)} concepts...")
        openai_analysis = analyze_concepts_with_openai(
            concepts=codes,
            clinical_text=clinical_text,
            patient_info=patient_info
        )
        
        if openai_analysis:
            print(f"DEBUG: AI analysis complete - DRG: {openai_analysis.primary_drg}, "
                  f"Complexity: {openai_analysis.complexity_level}")
            
            # Filter out excluded codes from the table
            excluded_icd10_codes = set()
            if openai_analysis.excluded_codes:
                for excluded in openai_analysis.excluded_codes:
                    excluded_icd10_codes.add(excluded.get('code', ''))
            
            # Filter codes - remove excluded ones
            filtered_codes = []
            excluded_concepts = []
            
            for concept in codes:
                if concept.get('icd10_codes'):
                    icd10_code = concept['icd10_codes'][0].get('code', '')
                    if icd10_code in excluded_icd10_codes:
                        excluded_concepts.append(concept)
                    else:
                        filtered_codes.append(concept)
                else:
                    filtered_codes.append(concept)
            
            # Create comprehensive response
            return jsonify({
                'success': True,
                'codes': filtered_codes,
                'excluded_concepts': excluded_concepts,
                'excluded_codes_info': openai_analysis.excluded_codes,
                'ai_analysis': {
                    'method': 'OpenAI GPT-4o Analysis',
                    'primary_drg': openai_analysis.primary_drg,
                    'drg_description': openai_analysis.drg_description,
                    'complexity': openai_analysis.complexity_level,
                    'reasoning': openai_analysis.clinical_reasoning,
                    'rationale': openai_analysis.complexity_rationale,
                    'confidence': openai_analysis.confidence_score,
                    'supporting_concepts': openai_analysis.supporting_concepts,
                    'secondary_drgs': openai_analysis.secondary_drgs
                }
            })
        else:
            return jsonify({
                'error': 'AI analysis failed',
                'message': 'OpenAI analysis returned no results'
            }), 500
            
    except Exception as e:
        print(f"ERROR: AI analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'error': 'AI analysis failed',
            'message': str(e)
        }), 500

@main.route('/', methods=['GET', 'POST'])
def process_text():
    form = ClinicalNoteForm()
    codes = None  # default
    # Apply config default for initial inpatient checkbox if no POST
    if request.method == 'GET':
        try:
            default_flag = current_app.config.get('INPATIENT_DRG_DEFAULT', 0)
            form.inpatient.data = bool(default_flag)
        except Exception:
            pass

    if request.method == 'POST':
        clinical_text = request.form.get('clinical_note', '').strip()
        print(f"DEBUG: POST received with text: {clinical_text}")

        if clinical_text:  # Simple validation instead of form.validate_on_submit()
            # Save to history
            try:
                from app.models.db import ClinicalNoteHistory, db
                preview = clinical_text[:200] if len(clinical_text) > 200 else clinical_text
                history_entry = ClinicalNoteHistory(
                    clinical_text=clinical_text,
                    preview=preview
                )
                db.session.add(history_entry)
                db.session.commit()
            except Exception as e:
                print(f"DEBUG: Failed to save history: {e}")
            
            # (Optional) could also read from form object if WTForms field present
            # clinical_text = form.clinical_note.data
            try:
                from app.nlp.rag_pipeline import get_rag_pipeline
                umls_path = current_app.config.get('UMLS_PATH', 'umls_data')
                nlp_pipeline = get_rag_pipeline(umls_path)
                codes = nlp_pipeline.process_text(clinical_text)
                print(f"DEBUG: Raw extracted codes (RAG path) count={len(codes)} sample={codes[:3] if codes else []}")
                if not codes:
                    print("DEBUG: RAG pipeline returned 0 codes, falling back to base pipeline")
                    base_pipeline = get_nlp()
                    codes = base_pipeline.process_text(clinical_text)
                    print(f"DEBUG: Base pipeline after RAG-empty produced {len(codes)} codes")
                # Normalize CUIs first
                try:
                    from app.utils.cui_normalization import get_canonical_cui
                    for c in codes:
                        canon = get_canonical_cui(c.get('cui'))
                        if canon and canon != c.get('cui'):
                            c['original_cui'] = c['cui']
                            c['cui'] = canon
                except Exception:
                    pass
                # Backfill codes if missing (RAG may not include all code types)
                from app.utils.umls_lookup import get_codes_for_cui as _lookup_codes
                for c in codes:
                    if (not c.get('icd10_codes')) or (not c.get('snomed_codes')):
                        extra = _lookup_codes(c['cui'], umls_path)
                        if not c.get('icd10_codes'):
                            c['icd10_codes'] = extra.get('icd10_codes', [])
                        if not c.get('snomed_codes'):
                            c['snomed_codes'] = extra.get('snomed_codes', [])
            except Exception as e:
                nlp_pipeline = get_nlp()
                codes = nlp_pipeline.process_text(clinical_text)
                print(f"DEBUG: Raw extracted codes (fallback base pipeline) count={len(codes)} sample={codes[:3] if codes else []}")
                from app.utils.umls_lookup import get_codes_for_cui
                umls_path = current_app.config.get('UMLS_PATH', 'umls_data')
                for c in codes:
                    extra_codes = get_codes_for_cui(c['cui'], umls_path)
                    c['snomed_codes'] = extra_codes.get('snomed_codes', [])
                    c['icd10_codes'] = extra_codes.get('icd10_codes', [])

        try:
            sim_cutoff = float(request.form.get('similarity_cutoff', 0))
        except Exception:
            sim_cutoff = 0

        if codes is not None:
            filtered_codes = []
            for c in codes:
                relevance_score = c.get('rag_relevance', c.get('similarity', 0))
                if relevance_score >= sim_cutoff:
                    filtered_codes.append(c)
            codes = filtered_codes

            if request.form.get('only_icd10'):
                codes = [c for c in codes if c.get('icd10_codes') and len(c['icd10_codes']) > 0]

            codes = sorted(codes, key=lambda c: c.get('rag_relevance', c.get('similarity', 0)), reverse=True)

            seen_icd10 = set()
            deduped = []
            for entry in codes:
                icd_list = entry.get('icd10_codes') or []
                raw_codes = [i.get('code') for i in icd_list if isinstance(i, dict) and i.get('code')]
                if not raw_codes:
                    deduped.append(entry)
                    continue
                if any(rc in seen_icd10 for rc in raw_codes):
                    continue
                for rc in raw_codes:
                    seen_icd10.add(rc)
                deduped.append(entry)
            codes = deduped
            
            # Update history entry with codes count
            try:
                from app.models.db import ClinicalNoteHistory, db
                last_entry = ClinicalNoteHistory.query.order_by(ClinicalNoteHistory.id.desc()).first()
                if last_entry and last_entry.clinical_text == clinical_text:
                    last_entry.codes_count = len(codes)
                    db.session.commit()
            except Exception as e:
                print(f"DEBUG: Failed to update history codes count: {e}")

            # DRG enrichment only if inpatient flag set in form (checkbox)
            inpatient_selected = bool(request.form.get('inpatient')) or bool(request.form.get('inpatient', False))
            drg_rationale = None
            openai_analysis = None
            
            if inpatient_selected:
                # NEW: AI-Powered DRG Analysis using OpenAI GPT-4o (Second Step)
                use_openai_drg = os.environ.get('ENABLE_OPENAI_DRG', '0') == '1'
                
                if use_openai_drg:
                    try:
                        from app.ai.openai_drg_analyzer import analyze_concepts_with_openai
                        
                        # Extract patient demographics if available from text
                        patient_info = {}
                        age_match = re.search(r'(\d+)[-\s]?year[-\s]?old', clinical_text, re.IGNORECASE)
                        if age_match:
                            patient_info['age'] = age_match.group(1)
                        
                        gender_match = re.search(r'\b(male|female|man|woman)\b', clinical_text, re.IGNORECASE)
                        if gender_match:
                            patient_info['gender'] = gender_match.group(1)
                        
                        print(f"DEBUG: Starting OpenAI DRG analysis for {len(codes)} concepts...")
                        openai_analysis = analyze_concepts_with_openai(
                            concepts=codes,
                            clinical_text=clinical_text,
                            patient_info=patient_info
                        )
                        
                        if openai_analysis:
                            print(f"DEBUG: OpenAI analysis complete - DRG: {openai_analysis.primary_drg}, "
                                  f"Complexity: {openai_analysis.complexity_level}")
                            
                            # Apply OpenAI analysis results to codes
                            for c in codes:
                                # Clear any existing DRG codes from heuristic method
                                c['drg_codes'] = []
                                
                                # Add AI-determined DRG if this concept is relevant
                                if openai_analysis.primary_drg and (
                                    c.get('term', '').lower() in [sc.lower() for sc in openai_analysis.supporting_concepts] or
                                    any(icd.get('code', '') in str(openai_analysis.clinical_reasoning) 
                                        for icd in c.get('icd10_codes', []))
                                ):
                                    c['drg_codes'].append({
                                        'drg': openai_analysis.primary_drg,
                                        'description': openai_analysis.drg_description or 'AI-determined DRG',
                                        'complexity': openai_analysis.complexity_level,
                                        'confidence': openai_analysis.confidence_score,
                                        'ai_powered': True
                                    })
                            
                            # Create comprehensive rationale
                            drg_rationale = {
                                'method': 'OpenAI GPT-4o Analysis',
                                'primary_drg': openai_analysis.primary_drg,
                                'complexity': openai_analysis.complexity_level,
                                'reasoning': openai_analysis.clinical_reasoning,
                                'rationale': openai_analysis.complexity_rationale,
                                'confidence': openai_analysis.confidence_score,
                                'supporting_concepts': openai_analysis.supporting_concepts,
                                'secondary_drgs': openai_analysis.secondary_drgs
                            }
                        else:
                            print("DEBUG: OpenAI analysis returned None - falling back to heuristic method")
                            
                    except Exception as e:
                        print(f"DEBUG: OpenAI DRG analysis failed: {e} - falling back to heuristic method")
                        openai_analysis = None
                
                # Fallback to traditional heuristic DRG method if OpenAI fails or is disabled
                if not openai_analysis and drg_enabled():
                    print("DEBUG: Using traditional heuristic DRG method")
                    enrich_codes_with_drgs(codes)
                    try:
                        from app.drg.severity import apply_drg_severity_selection
                        drg_rationale = apply_drg_severity_selection(codes)
                        if drg_rationale:
                            drg_rationale['method'] = 'Heuristic Analysis'
                    except Exception:
                        drg_rationale = None
            else:
                # Outpatient - clear DRG codes
                for c in codes:
                    c['drg_codes'] = []

            # Persist extracted codes (optional; can be disabled if noisy)
            try:
                for c in codes:
                    new_code = ExtractedCode(
                        document_id='manual',
                        code_type=', '.join(c.get('semtypes', [])),
                        code_value=c.get('cui'),
                        description=c.get('term'),
                        confidence=c.get('rag_relevance', c.get('similarity', 0)),
                        source_text=clinical_text,
                        validated=False
                    )
                    db.session.add(new_code)
                db.session.commit()
            except Exception as e:
                print(f"WARN: Failed to persist extracted codes: {e}")
                db.session.rollback()

            from app.utils.semantic_types import SEMANTIC_TYPE_MAP
            print(f"DEBUG: Returning {len(codes)} codes to template")
            return render_template('index.html', form=form, codes=codes, semtype_map=SEMANTIC_TYPE_MAP, inpatient_selected=inpatient_selected, drg_rationale=drg_rationale)

    from app.utils.semantic_types import SEMANTIC_TYPE_MAP
    return render_template('index.html', form=form, codes=None, semtype_map=SEMANTIC_TYPE_MAP, inpatient_selected=form.inpatient.data, drg_rationale=None)


@main.route('/history', methods=['GET'])
def get_history():
    """
    Get clinical note history
    """
    try:
        from app.models.db import ClinicalNoteHistory
        limit = request.args.get('limit', 10, type=int)
        history_entries = ClinicalNoteHistory.query.order_by(
            ClinicalNoteHistory.created_at.desc()
        ).limit(limit).all()
        
        history_list = []
        for entry in history_entries:
            history_list.append({
                'id': entry.id,
                'preview': entry.preview,
                'created_at': entry.created_at.isoformat(),
                'codes_count': entry.codes_count
            })
        
        return jsonify({
            'success': True,
            'history': history_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@main.route('/history/<int:history_id>', methods=['GET'])
def get_history_item(history_id):
    """
    Get full text of a specific history item
    """
    try:
        from app.models.db import ClinicalNoteHistory
        entry = ClinicalNoteHistory.query.get_or_404(history_id)
        
        return jsonify({
            'success': True,
            'id': entry.id,
            'clinical_text': entry.clinical_text,
            'created_at': entry.created_at.isoformat(),
            'codes_count': entry.codes_count
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@main.route('/history/<int:history_id>', methods=['DELETE'])
def delete_history_item(history_id):
    """
    Delete a specific clinical note history entry
    """
    try:
        from app.models.db import ClinicalNoteHistory, db
        history_entry = ClinicalNoteHistory.query.get(history_id)
        
        if not history_entry:
            return jsonify({
                'success': False,
                'error': 'History entry not found'
            }), 404
        
        db.session.delete(history_entry)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'History entry deleted successfully'
        })
    except Exception as e:
        from app.models.db import db
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@main.route('/history/all', methods=['DELETE'])
def delete_all_history():
    """
    Delete all clinical note history entries
    """
    try:
        from app.models.db import ClinicalNoteHistory, db
        count = ClinicalNoteHistory.query.delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Deleted {count} history entries',
            'count': count
        })
    except Exception as e:
        from app.models.db import db
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@main.route('/search', methods=['POST'])
def semantic_search():
    query = request.json.get('query')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    try:
        from app.nlp.rag_pipeline import get_rag_pipeline
        umls_path = current_app.config.get('UMLS_PATH', 'umls_data')
        nlp_pipeline = get_rag_pipeline(umls_path)
        results = nlp_pipeline.search_semantic(query, top_k=10)
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': f'Semantic search failed: {str(e)}'}), 500