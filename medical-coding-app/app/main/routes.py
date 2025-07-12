from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from app import get_nlp
from app.utils.audit import log_audit_trail
from .forms import ClinicalNoteForm
from app.models.db import ExtractedCode, db
from . import main

@main.route('/extract', methods=['POST'])
def extract_codes_route():
    clinical_text = request.json.get('clinical_text')
    if not clinical_text:
        return jsonify({'error': 'No clinical text provided'}), 400

    nlp_pipeline = get_nlp()
    codes = nlp_pipeline.process_text(clinical_text)

    log_audit_trail(clinical_text, codes)

    return jsonify({'codes': codes})

@main.route('/', methods=['GET', 'POST'])
def process_text():
    form = ClinicalNoteForm()
    if form.validate_on_submit():
        clinical_text = form.clinical_note.data
        
        nlp_pipeline = get_nlp()
        codes = nlp_pipeline.process_text(clinical_text)

        # Get similarity threshold from form (default 0)
        try:
            sim_cutoff = float(request.form.get('similarity_cutoff', 0))
        except Exception:
            sim_cutoff = 0

        # Filter codes by similarity
        codes = [c for c in codes if c.get('similarity', 0) >= sim_cutoff]

        # Enrich each code with SNOMED & ICD-10 mappings (with descriptions)
        from app.utils.umls_lookup import get_codes_for_cui
        umls_path = current_app.config.get('UMLS_PATH', 'umls_data')
        for c in codes:
            extra_codes = get_codes_for_cui(c['cui'], umls_path)
            c['snomed_codes'] = extra_codes.get('snomed_codes', [])
            c['icd10_codes'] = extra_codes.get('icd10_codes', [])

        # If 'only_icd10' is checked, filter codes to those with at least one ICD-10 mapping
        if request.form.get('only_icd10'):
            codes = [c for c in codes if c.get('icd10_codes') and len(c['icd10_codes']) > 0]

        # Sort codes by similarity descending
        codes = sorted(codes, key=lambda c: c.get('similarity', 0), reverse=True)
        
        # Save to DB and render for manual validation
        for c in codes:
            new_code = ExtractedCode(
                document_id='manual',
                code_type=', '.join(c['semtypes']), # Storing semtypes in code_type
                code_value=c['cui'],
                description=c['term'],
                confidence=c['similarity'],
                source_text=clinical_text,
                validated=False
            )
            db.session.add(new_code)
        db.session.commit()
        
        from app.utils.semantic_types import SEMANTIC_TYPE_MAP
        flash('Codes extracted. Please validate.', 'success')
        return render_template('index.html', form=form, codes=codes, semtype_map=SEMANTIC_TYPE_MAP)
        
    from app.utils.semantic_types import SEMANTIC_TYPE_MAP
    return render_template('index.html', form=form, codes=None, semtype_map=SEMANTIC_TYPE_MAP)