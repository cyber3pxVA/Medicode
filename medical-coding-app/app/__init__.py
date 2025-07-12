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

    # The nlp blueprint can be removed if it has no routes
    # from .nlp import nlp as nlp_blueprint
    # app.register_blueprint(nlp_blueprint)

    return app