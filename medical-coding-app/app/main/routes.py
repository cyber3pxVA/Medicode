from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from app import get_nlp
from app.utils.audit import log_audit_trail
from .forms import ClinicalNoteForm
from app.models.db import ExtractedCode, db
from . import main

# DRG mapping (optional enrichment)
try:
    from app.utils.drg_mapping import get_drg_for_icd10
except Exception:  # Fails silently if module missing
    def get_drg_for_icd10(_):
        return []

@main.route('/extract', methods=['POST'])
def extract_codes_route():
    clinical_text = request.json.get('clinical_text')
    if not clinical_text:
        return jsonify({'error': 'No clinical text provided'}), 400

    # Use RAG-enhanced pipeline if available, fallback to base pipeline
    try:
        from app.nlp.rag_pipeline import get_rag_pipeline
        umls_path = current_app.config.get('UMLS_PATH', 'umls_data')
        nlp_pipeline = get_rag_pipeline(umls_path)
        codes = nlp_pipeline.process_text(clinical_text)
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

    # DRG enrichment based on ICD-10 codes
    for c in codes:
        drg_set = []
        for icd_entry in c.get('icd10_codes', []) or []:
            icd_code = icd_entry.get('code') if isinstance(icd_entry, dict) else None
            if icd_code:
                drgs = get_drg_for_icd10(icd_code)
                for d in drgs:
                    if d not in drg_set:
                        drg_set.append(d)
        c['drg_codes'] = drg_set

    log_audit_trail(clinical_text, codes)
    return jsonify({'codes': codes})

@main.route('/', methods=['GET', 'POST'])
def process_text():
    form = ClinicalNoteForm()
    if form.validate_on_submit():
        clinical_text = form.clinical_note.data
        try:
            from app.nlp.rag_pipeline import get_rag_pipeline
            umls_path = current_app.config.get('UMLS_PATH', 'umls_data')
            nlp_pipeline = get_rag_pipeline(umls_path)
            codes = nlp_pipeline.process_text(clinical_text)
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

        # DRG enrichment
        for c in codes:
            drg_set = []
            for icd_entry in c.get('icd10_codes', []) or []:
                icd_code = icd_entry.get('code') if isinstance(icd_entry, dict) else None
                if icd_code:
                    drgs = get_drg_for_icd10(icd_code)
                    for d in drgs:
                        if d not in drg_set:
                            drg_set.append(d)
            c['drg_codes'] = drg_set

        for c in codes:
            new_code = ExtractedCode(
                document_id='manual',
                code_type=', '.join(c['semtypes']),
                code_value=c['cui'],
                description=c['term'],
                confidence=c.get('rag_relevance', c.get('similarity', 0)),
                source_text=clinical_text,
                validated=False
            )
            db.session.add(new_code)
        db.session.commit()

        from app.utils.semantic_types import SEMANTIC_TYPE_MAP
        flash('Codes extracted with RAG enhancement. Please validate.', 'success')
        return render_template('index.html', form=form, codes=codes, semtype_map=SEMANTIC_TYPE_MAP)

    from app.utils.semantic_types import SEMANTIC_TYPE_MAP
    return render_template('index.html', form=form, codes=None, semtype_map=SEMANTIC_TYPE_MAP)

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