from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class ClinicalNote(db.Model):
    __tablename__ = 'clinical_notes'
    
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class CodeMapping(db.Model):
    __tablename__ = 'code_mappings'
    
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('clinical_notes.id'), nullable=False)
    code = db.Column(db.String(50), nullable=False)
    code_type = db.Column(db.String(10), nullable=False)  # ICD-10, SNOMED-CT, CPT
    confidence_score = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    clinical_note = db.relationship('ClinicalNote', backref=db.backref('mappings', lazy=True))

class ExtractedCode(db.Model):
    """
    ORM model for extracted_codes table.
    Stores extracted medical codes and related metadata.
    """
    __tablename__ = 'extracted_codes'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.String, nullable=False)
    code_type = db.Column(db.String, nullable=False)  # ICD-10, SNOMED, CPT
    code_value = db.Column(db.String, nullable=False)
    description = db.Column(db.Text, nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    source_text = db.Column(db.Text, nullable=False)
    validated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

class ProcessingLog(db.Model):
    """
    ORM model for processing_logs table.
    Stores logs for each document processed.
    """
    __tablename__ = 'processing_logs'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.String, nullable=False)
    processing_time = db.Column(db.Float, nullable=False)
    errors = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())