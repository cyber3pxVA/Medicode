import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_default_secret_key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UMLS_API_KEY = os.environ.get('UMLS_API_KEY')
    UMLS_PATH = os.environ.get('UMLS_PATH') or 'umls_data'
    DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')