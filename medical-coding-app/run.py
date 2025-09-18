import os
from app import create_app
from config import Config

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional; warn in README if not installed

app = create_app(Config)

if __name__ == "__main__":
    # Cloud Run provides PORT environment variable, default to 8080 for compatibility
    port = int(os.environ.get("PORT", 8080))
    
    # Disable debug mode in production (Cloud Run)
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    
    # Note: The host must be '0.0.0.0' to be accessible from outside the container
    app.run(host='0.0.0.0', port=port, debug=debug_mode)