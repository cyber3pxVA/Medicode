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
    # Note: The host must be '0.0.0.0' to be accessible from outside the container
    app.run(host='0.0.0.0', debug=True)