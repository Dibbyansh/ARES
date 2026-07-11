# Telegram integration — sends alert messages via the Bot API
import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


def send_telegram_alert(message):
    """Send message via Telegram API. Returns True on success."""
    
    # Silently skip if Telegram is not configured
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            return True
        else:
            print(f"⚠️  Telegram API returned status {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        print("⚠️  Telegram request timed out")
        return False
        
    except requests.exceptions.RequestException as error:
        print(f"⚠️  Could not send Telegram message: {error}")
        return False
    
    except Exception as error:
        print(f"⚠️  Unexpected error sending Telegram: {error}")
        return False
