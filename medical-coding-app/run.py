import os
import threading
import subprocess
import time
from app import create_app
from config import Config

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional; warn in README if not installed

# Global variables for tracking initialization status
umls_init_status = {
    'initialized': False,
    'initializing': False,
    'error': None,
    'progress': 'Not started'
}

def init_umls_background():
    """Initialize UMLS data in background thread"""
    global umls_init_status
    
    try:
        umls_init_status['initializing'] = True
        umls_init_status['progress'] = 'Downloading UMLS data from Cloud Storage...'
        
        # Run UMLS initialization
        result = subprocess.run(['python', 'init_umls_from_storage.py'], 
                               capture_output=True, text=True, timeout=1800)  # 30min timeout
        
        if result.returncode != 0:
            raise Exception(f"UMLS init failed: {result.stderr}")
        
        umls_init_status['progress'] = 'Initializing database...'
        
        # Run database initialization
        result = subprocess.run(['python', 'init_db.py'], 
                               capture_output=True, text=True, timeout=300)  # 5min timeout
        
        if result.returncode != 0:
            raise Exception(f"DB init failed: {result.stderr}")
        
        umls_init_status['initialized'] = True
        umls_init_status['initializing'] = False
        umls_init_status['progress'] = 'Complete - UMLS and NLP pipeline ready'
        print("✅ Background UMLS initialization completed successfully")
        
    except Exception as e:
        umls_init_status['initializing'] = False
        umls_init_status['error'] = str(e)
        umls_init_status['progress'] = f'Failed: {str(e)}'
        print(f"❌ Background UMLS initialization failed: {e}")

app = create_app(Config)

# Add health check endpoints
@app.route('/health')
def health_check():
    """Basic health check - app is running"""
    return {'status': 'healthy', 'message': 'Flask app is running'}, 200

@app.route('/ready')
def readiness_check():
    """Readiness check - app is ready for requests"""
    global umls_init_status
    
    if umls_init_status['initialized']:
        return {'status': 'ready', 'message': 'UMLS and NLP pipeline ready'}, 200
    elif umls_init_status['initializing']:
        return {
            'status': 'initializing', 
            'message': 'UMLS data loading in background',
            'progress': umls_init_status['progress']
        }, 202
    elif umls_init_status['error']:
        return {
            'status': 'error', 
            'message': 'UMLS initialization failed',
            'error': umls_init_status['error']
        }, 503
    else:
        return {
            'status': 'starting', 
            'message': 'UMLS initialization not started'
        }, 202

if __name__ == "__main__":
    # Cloud Run provides PORT environment variable, default to 8080 for compatibility
    port = int(os.environ.get("PORT", 8080))
    
    # Disable debug mode in production (Cloud Run)
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    
    # Start UMLS initialization in background after a short delay
    def delayed_umls_init():
        time.sleep(5)  # Give Flask time to start
        if not umls_init_status['initializing'] and not umls_init_status['initialized']:
            print("🚀 Starting background UMLS initialization...")
            umls_thread = threading.Thread(target=init_umls_background, daemon=True)
            umls_thread.start()
    
    init_thread = threading.Thread(target=delayed_umls_init, daemon=True)
    init_thread.start()
    
    print(f"🌐 Starting Flask app on port {port}")
    print("📡 UMLS initialization will begin in background shortly...")
    print("🔍 Check /health for app status and /ready for UMLS status")
    
    # Note: The host must be '0.0.0.0' to be accessible from outside the container
    app.run(host='0.0.0.0', port=port, debug=debug_mode)