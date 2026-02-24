import os
import sys
import json
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from orbiter.bot.sheets import update_engine_state
except ImportError:
    print("❌ Error: Could not import sheets module. Ensure you are in the correct directory.")
    sys.exit(1)

def main():
    print("🌀 --- ORBITER FORCE SYNC TOOL ---")
    
    # Path to the session state file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    state_path = os.path.join(base_dir, "orbiter", "data", "session_state.json")
    
    if not os.path.exists(state_path):
        print(f"❌ State file not found at: {state_path}")
        # Create a dummy empty state if needed to at least clear the cloud stale state
        print("💡 Suggestion: If you want to start fresh, just run the MBC directly.")
        return

    try:
        with open(state_path, 'r') as f:
            state_data = json.load(f)
            
        # Update timestamp to now to pass the freshness check on MBC
        state_data['last_updated'] = time.time()
        json_str = json.dumps(state_data)
        
        print(f"📄 Local state loaded (Last Updated: {datetime.fromtimestamp(state_data.get('last_updated', 0)).strftime('%H:%M:%S')})")
        print(f"📂 Active Positions: {len(state_data.get('active_positions', {}))}")
        
        print("☁️  Uploading to Google Sheets 'engine_state'...")
        update_engine_state(json_str)
        print("✅ Force Sync Successful. You can now run ./start_office.sh on your MacBook.")
        
    except Exception as e:
        print(f"❌ Failed to sync: {e}")

if __name__ == "__main__":
    main()
