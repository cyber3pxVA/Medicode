import os
import json
from app import create_app

def make_client(inpatient_default=0):
    os.environ['INPATIENT_DRG_DEFAULT'] = str(inpatient_default)
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()

# Simple monkey patch for drg mapping during tests
class DummyDRG:
    def __init__(self, drg, description):
        self.drg = drg
        self.description = description

def test_extract_api_outpatient():
    client = make_client(0)
    # Without inpatient=1 param no drg_codes
    resp = client.post('/extract', json={'clinical_text': 'hypertension'})
    data = resp.get_json()
    assert 'codes' in data
    for c in data['codes']:
        assert c.get('drg_codes') == []


def test_extract_api_inpatient():
    client = make_client(0)
    # Force inpatient flag
    resp = client.post('/extract?inpatient=1', json={'clinical_text': 'hypertension'})
    data = resp.get_json()
    assert 'codes' in data
    # drg_codes may still be empty if no mapping loaded; ensure field present
    for c in data['codes']:
        assert 'drg_codes' in c

