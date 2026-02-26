import requests
import yaml
import os
import sys
import time
import threading
import traceback

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

        # 🔥 Debug: Log where we are sending
        safe_token = f"{token[:5]}...{token[-5:]}" if token else "None"
        print(f"📤 Telegram Sending to {chat_id} via {safe_token}")

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML" # 🔥 Switched to HTML for maximum reliability
        }

        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            print(f"❌ Telegram API Error {response.status_code}: {response.text}")
        return response.status_code == 200

    except Exception as e:
        print(f"❌ Telegram Exception: {e}")
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
        self._frozen = False
        self._auto_unfreeze_scheduled = False
        
    def start(self):
        if self.token and not self.running:
            self.running = True
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()
            print("🎧 Telegram Command Listener started.")

    def is_frozen(self):
        """Check if trading is frozen"""
        return self._frozen
        
    def freeze(self):
        """Freeze trading"""
        self._frozen = True
        print("❄️ Trading frozen via Telegram")
        
    def unfreeze(self):
        """Unfreeze trading"""
        self._frozen = False
        self._auto_unfreeze_scheduled = False
        print("▶️ Trading unfrozen via Telegram")

    def _listen_loop(self):
        import pytz
        while self.running:
            # Check for auto-unfreeze at 15:30 IST
            if self._frozen and self._auto_unfreeze_scheduled:
                import datetime
                ist = pytz.timezone('Asia/Kolkata')
                now = datetime.datetime.now(ist)
                if now.hour == 15 and now.minute >= 30:
                    self.unfreeze()
                    send_telegram_msg("☀️ <b>AUTO-UNFREEZE</b>\n\nNFO session ended. Trading enabled.")
            
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
                        else:
                            print(f"🚫 Unauthorized Telegram access attempt from ID: {from_id} (Expected: {self.chat_id})")
                
            except Exception as e:
                print(f"⚠️ Telegram Listener Error: {e}")
            
            time.sleep(1)

    def _handle_command(self, text):
        now = time.time()
        print(f"📥 Telegram Command Received: {text}")
        cmd = text.lower().split()[0] if text else ""
        
        try:
            if cmd == "/q":
                question = text[2:].strip()
                if not question:
                    send_telegram_msg("❓ <b>Usage:</b> <code>/q why was trade not taken for RELIANCE?</code>")
                    return
                if "query" in self.callbacks:
                    send_telegram_msg("🤖 <b>Thinking...</b>")
                    try:
                        msg = self.callbacks["query"](question)
                        send_telegram_msg(msg)
                    except Exception as ai_err:
                        print(f"❌ AI Callback Error: {ai_err}")
                        send_telegram_msg(f"❌ <b>AI Error:</b> {ai_err}")
            elif cmd == "/margin":
                if "margin" in self.callbacks:
                    msg = self.callbacks["margin"]()
                    send_telegram_msg(msg)
            elif cmd == "/pnl":
                if "pnl" in self.callbacks:
                    msg = self.callbacks["pnl"]()
                    send_telegram_msg(msg)
            elif cmd == "/status":
                 if "status" in self.callbacks:
                    msg = self.callbacks["status"]()
                    send_telegram_msg(msg)
            elif cmd == "/version":
                if "version" in self.callbacks:
                    msg = self.callbacks["version"]()
                    send_telegram_msg(msg)
            elif cmd == "/scan":
                 if "scan" in self.callbacks:
                     msg = self.callbacks["scan"]()
                     send_telegram_msg(msg)
            elif cmd == "/freeze":
                self._frozen = True
                self._auto_unfreeze_scheduled = True
                msg = "❄️ <b>TRADING FROZEN</b>\n\nAll trade executions are blocked.\nAuto-unfreeze scheduled at 15:30."
                send_telegram_msg(msg)
                if "freeze" in self.callbacks:
                    self.callbacks["freeze"]()
            elif cmd == "/unfreeze":
                self._frozen = False
                self._auto_unfreeze_scheduled = False
                msg = "▶️ <b>TRADING UNFROZEN</b>\n\nAll trade executions enabled."
                send_telegram_msg(msg)
                if "unfreeze" in self.callbacks:
                    self.callbacks["unfreeze"]()
            elif cmd == "/help":
                msg = [
                    "🤖 <b>Orbiter C2 - Command Reference</b>",
                    "---",
                    "📊 <code>/status</code> - <b>The Big Picture:</b> Shows buying power and overnight status.",
                    "",
                    "💰 <code>/pnl</code> - <b>Live Profits:</b> Snapshot of active positions and floating PnL (₹).",
                    "",
                    "💰 <code>/margin</code> - <b>Wallet Check:</b> snapshot of available margin and utilization.",
                    "",
                    "🔍 <code>/scan</code> - <b>Market Pulse:</b> Live scan count and Top 10 movers.",
                    "",
                    "🤖 <code>/q &lt;question&gt;</code> - <b>AI Explainer:</b> Ask why a trade was taken.",
                    "",
                    "❄️ <code>/freeze</code> - <b>Freeze Trading:</b> Block all trade executions.",
                    "",
                    "▶️ <code>/unfreeze</code> - <b>Unfreeze Trading:</b> Enable trade executions.",
                    "",
                    "ℹ️ <code>/version</code> - <b>Bot Version</b>",
                    "",
                    "🧹 <code>/cleanup</code> - <b>Reset Logs</b>"
                ]
                send_telegram_msg("\n".join(msg))
            elif text == "/cleanup":
                self._cleanup_pending = True
                self._cleanup_timestamp = now
                send_telegram_msg("⚠️ <b>CRITICAL:</b> This will delete ALL trade logs.\nSend <code>/confirm_cleanup</code> within 60s.")
            elif text == "/confirm_cleanup":
                if self._cleanup_pending and (now - self._cleanup_timestamp < 60):
                    self._cleanup_pending = False
                    send_telegram_msg("🧹 <b>Cleanup in progress...</b>")
                    if "cleanup" in self.callbacks:
                        self.callbacks["cleanup"]()
                        send_telegram_msg("✨ <b>Google Sheets Cleanup Complete!</b>")
                else:
                    self._cleanup_pending = False
                    send_telegram_msg("❌ <b>Cleanup Cancelled:</b> Request expired.")
        except Exception as e:
            print(f"❌ Telegram Command Logic Crash: {e}")
            print(traceback.format_exc())
            send_telegram_msg(f"❌ <b>Internal Error:</b> Command handler crashed.")

if __name__ == "__main__":
    # Test script if run directly
    if len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
    else:
        msg = "🚀 <b>Orbiter Test Notification</b>\nSystem is online and connected!"
    
    if send_telegram_msg(msg):
        print("✅ Telegram message sent successfully!")
    else:
        print("❌ Failed to send Telegram message.")
