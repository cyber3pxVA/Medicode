from flask import Flask, g, current_app
from config import Config
from .models.db import db
from .nlp.pipeline import NLPPipeline

def get_nlp():
    """
    Connects to the NLP pipeline.
    """
    if 'nlp' not in g:
        g.nlp = NLPPipeline(current_app.config['UMLS_PATH'])
    return g.nlp

def create_app(config_object=None):
    app = Flask(__name__)

    if config_object:
        app.config.from_object(config_object)
    else:
        app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)

    # Set up a teardown function to close the NLP pipeline if needed
    # (though as a singleton, it might not need explicit closing)
    # @app.teardown_appcontext
    # def teardown_nlp(exception):
    #     nlp = g.pop('nlp', None)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Register lightweight health/feature endpoints here so test instances include them
    @app.route('/health')
    def _health():  # pragma: no cover - trivial
        meta = {}
        try:
            from app.utils.rag_enhanced_lookup import get_rag_lookup
            umls_path = app.config.get('UMLS_PATH', 'umls_data')
            lookup = get_rag_lookup(umls_path)
            meta['semantic_model'] = getattr(lookup, 'semantic_model_name', None)
        except Exception:
            meta['semantic_model'] = None
        return {'status': 'healthy', 'semantic_model': meta['semantic_model']}, 200

    @app.route('/features')
    def _features():  # pragma: no cover - trivial
        import os
        flags = {
            'USE_RAG': os.environ.get('USE_RAG', '0') == '1',
            'ENABLE_DRG': os.environ.get('ENABLE_DRG', '0') == '1',
            'KEEP_NEGATED': os.environ.get('KEEP_NEGATED', '0') == '1',
            'USE_MEDSPACY_CONTEXT': os.environ.get('USE_MEDSPACY_CONTEXT', '0') == '1'
        }
        model = None
        try:
            from app.utils.rag_enhanced_lookup import get_rag_lookup
            umls_path = app.config.get('UMLS_PATH', 'umls_data')
            lookup = get_rag_lookup(umls_path)
            model = getattr(lookup, 'semantic_model_name', None)
        except Exception:
            pass
        flags['SEMANTIC_MODEL'] = model
        return flags, 200

    # The nlp blueprint can be removed if it has no routes
    # from .nlp import nlp as nlp_blueprint
    # app.register_blueprint(nlp_blueprint)

    return app