from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    filename='audit.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_audit_trail(clinical_text, codes):
    """
    Logs the clinical text and the codes that were extracted.
    """
    logging.info(f"--- AUDIT TRAIL START ---")
    logging.info(f"Clinical Text: {clinical_text}")
    logging.info(f"Extracted Codes: {codes}")
    logging.info(f"--- AUDIT TRAIL END ---")

def log_audit_event(event_description):
    """Logs an audit event with a timestamp."""
    logging.info(event_description)

def log_code_extraction(code, confidence_score):
    """Logs the details of code extraction events."""
    event_description = f"Code extracted: {code}, Confidence score: {confidence_score}"
    log_audit_event(event_description)

def log_manual_validation(user_id, code, validation_status):
    """Logs manual validation events."""
    event_description = f"User {user_id} validated code: {code}, Status: {validation_status}"
    log_audit_event(event_description)