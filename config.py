# Loads environment variables and exposes app-wide settings
import os
from dotenv import load_dotenv

# Read .env file into process environment
load_dotenv()


def get_required_setting(setting_name):
    """Read a required .env variable or raise if missing."""
    value = os.getenv(setting_name)
    
    # Fail fast if a mandatory setting is missing
    if not value:
        error_message = f"""
        ❌ Missing required setting: {setting_name}
        
        How to fix:
        1. Copy .env.example to .env
        2. Open .env in a text editor
        3. Fill in the value for {setting_name}
        4. Save the file and try again
        """
        raise EnvironmentError(error_message)
    
    return value


# AI provider credentials and model
OPENROUTER_API_KEY = get_required_setting("OPENROUTER_API_KEY")

OPENROUTER_BASE_URL = get_required_setting("OPENROUTER_BASE_URL")

MODEL = get_required_setting("MODEL")

# PostgreSQL connection settings
DB_HOST = get_required_setting("DB_HOST")

DB_PORT = get_required_setting("DB_PORT")

DB_NAME = get_required_setting("DB_NAME")

DB_USER = get_required_setting("DB_USER")

DB_PASSWORD = get_required_setting("DB_PASSWORD")

# Telegram is optional — alerts are skipped when these are empty
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Confirm config loaded at import time
print("✓ Configuration loaded successfully!")
print(f"  - Using AI model: {MODEL}")
print(f"  - Database: {DB_NAME}")
if TELEGRAM_BOT_TOKEN:
    print(f"  - Telegram alerts: ENABLED")
else:
    print(f"  - Telegram alerts: DISABLED (optional)")
