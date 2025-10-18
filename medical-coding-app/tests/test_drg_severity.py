import os
import importlib


def test_drg_severity_selection(tmp_path):
    # Prepare a minimal heuristic mapping CSV with triads for pneumonia (J18) and sepsis (A41)
    mapping_csv = tmp_path / "drg_mapping_test.csv"
    mapping_csv.write_text("""ICD10,DRG,DRG_DESCRIPTION\nJ18,193,SIMPLE PNEUMONIA & PLEURISY W MCC\nJ18,194,SIMPLE PNEUMONIA & PLEURISY W CC\nJ18,195,SIMPLE PNEUMONIA & PLEURISY W/O CC/MCC\nA41,871,SEPTICEMIA OR SEVERE SEPSIS W MCC\nA41,872,SEPTICEMIA OR SEVERE SEPSIS W CC\nA41,873,SEPTICEMIA OR SEVERE SEPSIS W/O CC/MCC\n""")

    # Set environment vars BEFORE importing modules that cache mapping
    os.environ['ENABLE_DRG'] = '1'
    os.environ['DRG_MAPPING_PATH'] = str(mapping_csv)

    # Force reload mapping provider to pick up new path
    import app.utils.drg_mapping as dm
    importlib.reload(dm)
    import app.drg.provider as provider
    importlib.reload(provider)

    from app.drg.severity import apply_drg_severity_selection

    # Construct synthetic concepts similar to extraction output
    pneumonia = {
        'cui': 'AUTO_ICD_J18.9',
        'term': 'pneumonia',
        'negated': False,
        'icd10_codes': [{'code': 'J18.9', 'desc': 'Explicit mention'}],
        'drg_codes': []  # will be filled by enrichment
    }
    sepsis = {
        'cui': 'AUTO_ICD_A41.9',
        'term': 'sepsis',
        'negated': False,
        'icd10_codes': [{'code': 'A41.9', 'desc': 'Explicit mention'}],
        'drg_codes': []
    }
    codes = [pneumonia, sepsis]

    provider.enrich_codes_with_drgs(codes)

    rationale = apply_drg_severity_selection(codes)
    # Expect pneumonia chosen as principal and MCC severity selected due to sepsis MCC variant presence
    assert rationale is not None, 'Rationale should be produced'
    assert rationale['principal_icd'].startswith('J18')
    assert rationale['chosen_severity'] == 'MCC'
    # Principal concept should have chosen_drg severity MCC
    assert 'chosen_drg' in pneumonia
    assert pneumonia['chosen_drg']['severity'] == 'MCC'
