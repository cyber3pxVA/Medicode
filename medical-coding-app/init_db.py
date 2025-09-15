#!/usr/bin/env python3
"""
Database initialization script.
Creates all required tables for the medical coding application.
"""

from app import create_app
from app.models.db import db

def init_database():
    """Initialize the database with all required tables."""
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        
        # Create all tables
        db.create_all()
        
        print("✅ Database tables created successfully!")
        print("Tables created:")
        print("- clinical_notes")
        print("- code_mappings") 
        print("- extracted_codes")
        print("- processing_logs")

if __name__ == "__main__":
    init_database() 