import requests
import yaml
import os
import sys

# Path to find credentials
base_dir = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(base_dir, '../../ShoonyaApi-py/cred.yml')

def send_telegram_msg(message: str):
    """Send a message to the configured Telegram bot and chat."""
    try:
        if not os.path.exists(cred_path):
            print(f"❌ Telegram Error: Credential file not found at {cred_path}")
            return False

        with open(cred_path, 'r') as f:
            creds = yaml.safe_load(f)
        
        token = creds.get('telegram_token')
        chat_id = creds.get('telegram_chat_id')

        if not token or not chat_id:
            print("❌ Telegram Error: Token or Chat ID missing in cred.yml")
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }

        response = requests.post(url, data=payload, timeout=10)
        return response.status_code == 200

    except Exception as e:
        print(f"❌ Telegram Error: {e}")
        return False

if __name__ == "__main__":
    # Test script if run directly
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
    else:
        msg = "🚀 *Orbiter Test Notification*\nSystem is online and connected!"
    
    if send_telegram_msg(msg):
        print("✅ Telegram message sent successfully!")
    else:
        print("❌ Failed to send Telegram message.")
