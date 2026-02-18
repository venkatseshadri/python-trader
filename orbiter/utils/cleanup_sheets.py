import gspread
from google.oauth2.service_account import Credentials
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.sheets import (
    SCOPE, TRADE_LOG_HEADER, POSITIONS_HEADER, 
    CLOSED_POSITIONS_HEADER, SCAN_METRICS_HEADER
)

def cleanup_google_sheets(sheet_name="trade_log"):
    """
    🧹 Cleanup utility to reset trade logs and metrics.
    Preserves headers but clears all data rows.
    """
    print(f"🚀 Starting cleanup for Spreadsheet: '{sheet_name}'...")
    
    creds_path = os.path.join(os.path.dirname(__file__), "../bot/credentials.json")
    if not os.path.exists(creds_path):
        print(f"❌ Error: Credentials not found at {creds_path}")
        return

    try:
        creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
        client = gspread.authorize(creds)
        book = client.open(sheet_name)
        
        # Tabs to clear (Header, Tab Title)
        targets = [
            (TRADE_LOG_HEADER, "trade_log"),
            (POSITIONS_HEADER, "active_positions"),
            (CLOSED_POSITIONS_HEADER, "closed_positions"),
            (SCAN_METRICS_HEADER, "scan_metrics")
        ]
        
        for header, title in targets:
            try:
                sheet = book.worksheet(title)
                print(f"  🧹 Clearing '{title}'...")
                
                # Method: Clear everything and re-insert header
                sheet.clear()
                sheet.insert_row(header, 1)
                
                # Freeze the first row for better usability
                sheet.freeze(rows=1)
                
                print(f"  ✅ '{title}' reset successfully.")
            except gspread.exceptions.WorksheetNotFound:
                print(f"  ⚠️ Worksheet '{title}' not found. Skipping.")
            except Exception as e:
                print(f"  ❌ Error clearing '{title}': {e}")

        print("\n✨ Cleanup Complete! All logs have been reset.")
        print("💡 Note: 'control' and 'symbols' tabs were preserved.")

    except Exception as e:
        print(f"💥 Fatal Error: {e}")

if __name__ == "__main__":
    confirm = input("⚠️ This will PERMANENTLY DELETE all logged data in Google Sheets. Are you sure? (y/n): ")
    if confirm.lower() == 'y':
        cleanup_google_sheets()
    else:
        print("❌ Cleanup cancelled.")
