import os
from app import create_app

def make_client(flags=None):
    flags = flags or {}
    for k,v in flags.items():
        os.environ[k] = str(v)
    app = create_app()
    app.config['TESTING'] = True
    return app.test_client()


def test_health_endpoint():
    client = make_client()
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get('status') == 'healthy'
    assert 'semantic_model' in data


def test_features_endpoint_flags():
    client = make_client({'USE_RAG':1, 'ENABLE_DRG':1, 'KEEP_NEGATED':1})
    resp = client.get('/features')
    assert resp.status_code == 200
    data = resp.get_json()
    # Flags presence
    assert 'USE_RAG' in data and data['USE_RAG'] is True
    assert 'ENABLE_DRG' in data and data['ENABLE_DRG'] is True
    assert 'KEEP_NEGATED' in data and data['KEEP_NEGATED'] is True
    assert 'USE_MEDSPACY_CONTEXT' in data  # may be False by default
    # Model key always present (may be None before pipeline init)
    assert 'SEMANTIC_MODEL' in data
