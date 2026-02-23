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
        send_telegram_msg("/freeze")
        print("✅ Freeze signal broadcasted.")
    else:
        print("❌ Failed to send Telegram signal. Check credentials.")

    # 3. Peek Cloud State
    print("☁️  Fetching Cloud State from Google Sheets...")
    cloud_json = get_engine_state()
    session_recovered = False
    
    if cloud_json:
        data = json.loads(cloud_json)
        last_updated_ts = data.get('last_updated', 0)
        last_updated = datetime.fromtimestamp(last_updated_ts).strftime('%H:%M:%S')
        positions = data.get('active_positions', {})
        
        # Freshness Check: Only inherit if cloud state is < 4 hours old
        if (time.time() - last_updated_ts) < 14400:
            print("\n📈 --- CURRENT SESSION SNAPSHOT ---")
            print(f"🕒 Last Cloud Sync: {last_updated}")
            print(f"💰 Realized PnL: ₹{data.get('realized_pnl', 0):.2f}")
            print(f"📂 Active Positions: {len(positions)}")
            
            for token, pos in positions.items():
                print(f"  • {pos['symbol']}: {pos['strategy']} @ ₹{pos['entry_price']:.2f}")
            
            # 🔥 Write to local disk so main.py finds it immediately
            state_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "orbiter", "data")
            os.makedirs(state_dir, exist_ok=True)
            state_path = os.path.join(state_dir, "session_state.json")
            
            with open(state_path, 'w') as f:
                f.write(cloud_json)
            
            print(f"💾 Cloud state downloaded to: {state_path}")
            session_recovered = True
            print("-" * 40)
        else:
            print(f"⚠️  Cloud Snapshot is stale (Last sync: {last_updated}).")
    else:
        print("⚠️  No Cloud Snapshot found in Google Sheets.")

    # 4. Local Cleanup
    lock_file = ".orbiter.lock"
    if os.path.exists(lock_file):
        print("🧹 Removing stale local lockfile...")
        os.remove(lock_file)

    if session_recovered:
        print("\n✅ HANDOVER SUCCESSFUL!")
        print("You can now run: python orbiter/main.py")
    else:
        print("\n⚠️  HANDOVER INCOMPLETE: No active session recovered.")
        sys.exit(2) # Special exit code for "No Session"

if __name__ == "__main__":
    main()
