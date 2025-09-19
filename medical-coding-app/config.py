import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_default_secret_key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UMLS_API_KEY = os.environ.get('UMLS_API_KEY')
    UMLS_PATH = os.environ.get('UMLS_PATH') or 'umls_data'
    DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    
    # Authorized Users - Only these emails can access the application
    # This ensures UMLS license compliance by restricting access
    AUTHORIZED_USERS = os.environ.get('AUTHORIZED_USERS', '').split(',') if os.environ.get('AUTHORIZED_USERS') else [
        # Add your authorized user emails here
        # 'researcher@university.edu',
        # 'doctor@hospital.org',
    ]