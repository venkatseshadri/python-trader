import os
import sys
import json
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orbiter.utils.telegram_notifier import send_telegram_msg
from orbiter.bot.sheets import get_engine_state

def run_command(cmd, desc):
    print(f"📦 {desc}...")
    os.system(cmd)

def main():
    print("🏢 --- ORBITER OFFICE HANDOVER TOOL ---")
    print(f"🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("-" * 40)

    # 1. Sync Code
    run_command("git pull origin main", "Pulling latest code from GitHub")

    # 2. Remote Freeze
    print("❄️  Sending FREEZE signal to Remote (RPI) via Telegram...")
    if send_telegram_msg("❄️ <b>HANDOVER IN PROGRESS</b>: Freezing RPI instance..."):
        # We also need to send the actual command that the listener expects
        # Since we can't 'spoof' a message from the user easily, we tell the user to do it
        # OR we modify the main.py to handle a special 'handover' message
        send_telegram_msg("/freeze")
        print("✅ Freeze signal broadcasted.")
    else:
        print("❌ Failed to send Telegram signal. Check credentials.")

    # 3. Peek Cloud State
    print("☁️  Fetching Cloud State from Google Sheets...")
    cloud_json = get_engine_state()
    if cloud_json:
        data = json.loads(cloud_json)
        last_updated = datetime.fromtimestamp(data.get('last_updated', 0)).strftime('%H:%M:%S')
        positions = data.get('active_positions', {})
        
        print("
📈 --- CURRENT SESSION SNAPSHOT ---")
        print(f"🕒 Last Cloud Sync: {last_updated}")
        print(f"💰 Realized PnL: ₹{data.get('realized_pnl', 0):.2f}")
        print(f"🔢 Trade Count: {data.get('trade_count', 0)}")
        print(f"📂 Active Positions: {len(positions)}")
        
        for token, pos in positions.items():
            print(f"  • {pos['symbol']}: {pos['strategy']} @ ₹{pos['entry_price']:.2f}")
        print("-" * 40)
    else:
        print("⚠️  No Cloud Snapshot found in Google Sheets.")

    # 4. Local Cleanup
    lock_file = ".orbiter.lock"
    if os.path.exists(lock_file):
        print("🧹 Removing stale local lockfile...")
        os.remove(lock_file)

    print("
🚀 HANDOVER COMPLETE!")
    print("You can now run: python orbiter/main.py")

if __name__ == "__main__":
    main()
