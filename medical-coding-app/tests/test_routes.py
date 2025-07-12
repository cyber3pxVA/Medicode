import pytest
from app import create_app

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    UMLS_PATH = 'mock_umls_path'
    WTF_CSRF_ENABLED = False # Disable CSRF for testing forms

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app(TestConfig)
    yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

def test_index_page(client):
    """Test that the index page loads correctly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Medical Coding Application" in response.data

def test_extract_api_no_data(client):
    """Test the extract API with no data."""
    response = client.post('/extract', json={})
    assert response.status_code == 400
    assert b"No clinical text provided" in response.data

def test_extract_api_with_data(app, client, mocker):
    """Test the extract API with mocked NLP pipeline."""
    # Mock the get_nlp function to return a mock pipeline
    mock_pipeline = mocker.MagicMock()
    mock_pipeline.process_text.return_value = [
        {'cui': 'C0027051', 'term': 'Myocardial Infarction', 'similarity': 0.9, 'semtypes': ['dsyn']}
    ]
    mocker.patch('app.main.routes.get_nlp', return_value=mock_pipeline)

    response = client.post('/extract', json={'clinical_text': 'patient has MI'})
    
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'codes' in json_data
    assert len(json_data['codes']) == 1
    assert json_data['codes'][0]['cui'] == 'C0027051'

    # Ensure the mock was called
    mock_pipeline.process_text.assert_called_once_with('patient has MI')