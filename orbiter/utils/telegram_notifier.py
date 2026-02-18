import requests
import yaml
import os
import sys
import time
import threading

# Path to find credentials
base_dir = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(base_dir, '../../ShoonyaApi-py/cred.yml')

def get_creds():
    """Helper to get Telegram credentials from yaml."""
    if not os.path.exists(cred_path):
        return None, None
    with open(cred_path, 'r') as f:
        creds = yaml.safe_load(f)
    return creds.get('telegram_token'), creds.get('telegram_chat_id')

def send_telegram_msg(message: str):
    """Send a message to the configured Telegram bot and chat."""
    try:
        token, chat_id = get_creds()
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

class TelegramCommandListener:
    """
    🎧 Background listener for Telegram commands.
    """
    def __init__(self, callbacks: dict):
        self.token, self.chat_id = get_creds()
        self.callbacks = callbacks
        self.last_update_id = 0
        self.running = False
        self._thread = None
        self._cleanup_pending = False
        self._cleanup_timestamp = 0

    def start(self):
        if self.token and not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()
            print("🎧 Telegram Command Listener started.")

    def _listen_loop(self):
        while self.running:
            try:
                url = f"https://api.telegram.org/bot{self.token}/getUpdates"
                params = {"offset": self.last_update_id + 1, "timeout": 30}
                response = requests.get(url, params=params, timeout=35)
                
                if response.status_code == 200:
                    data = response.json()
                    for update in data.get("result", []):
                        self.last_update_id = update["update_id"]
                        message = update.get("message", {})
                        text = message.get("text", "")
                        from_id = str(message.get("from", {}).get("id", ""))
                        
                        # Only handle commands from the authorized chat_id
                        if from_id == str(self.chat_id):
                            self._handle_command(text.strip())
                
            except Exception as e:
                print(f"⚠️ Telegram Listener Error: {e}")
            
            time.sleep(1)

    def _handle_command(self, text):
        now = time.time()
        
        if text == "/margin":
            if "margin" in self.callbacks:
                msg = self.callbacks["margin"]()
                send_telegram_msg(msg)
        elif text == "/status":
             if "status" in self.callbacks:
                msg = self.callbacks["status"]()
                send_telegram_msg(msg)
        elif text == "/cleanup":
            self._cleanup_pending = True
            self._cleanup_timestamp = now
            send_telegram_msg("⚠️ *CRITICAL:* This will delete ALL trade logs and scan metrics.\nSend `/confirm_cleanup` within 60s to proceed.")
        elif text == "/confirm_cleanup":
            if self._cleanup_pending and (now - self._cleanup_timestamp < 60):
                self._cleanup_pending = False
                send_telegram_msg("🧹 *Cleanup in progress...*")
                if "cleanup" in self.callbacks:
                    self.callbacks["cleanup"]()
                    send_telegram_msg("✨ *Google Sheets Cleanup Complete!*")
            else:
                self._cleanup_pending = False
                send_telegram_msg("❌ *Cleanup Cancelled:* No pending request or time expired.")

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
