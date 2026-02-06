import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os

SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def log_buy_signals(buy_signals):
    """Log ONLY 45pt+ BUY trades to Google Sheets"""
    if not buy_signals:
        return
    
    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open("ORBiter Signals").sheet1
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    
    for signal in buy_signals:
        row = [
            timestamp,
            signal.get('token', 'N/A'),
            signal.get('symbol', 'N/A'),
            f"₹{signal.get('ltp', 0):.2f}",
            f"₹{signal.get('orb_high', 0):.2f}",
            f"₹{signal.get('ema5', 0):.2f}",
            signal.get('score', 0),
            "🚀 AUTO-BUY"  # Trade status
        ]
        sheet.append_row(row)
    
    print(f"✅ {len(buy_signals)} BUY signals → Google Sheets @ {timestamp}")
