import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os

SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

def log_buy_signals(buy_signals):
    """Log ONLY 45pt+ BUY trades to Google Sheets with symbol and company name"""
    if not buy_signals:
        return

    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open("trade_log").sheet1
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    for signal in buy_signals:
        # ✅ USE SIGNAL DATA DIRECTLY (already has symbol from rank_signals())
        row = [
            timestamp,
            signal.get('token', 'N/A'),                    # NSE|1394
            signal.get('symbol', 'UNKNOWN'),               # RELIANCE, ITC ✅ Company symbol
            signal.get('company_name', signal.get('symbol', 'N/A')),  # RELIANCE INDUSTRIES LIMITED
            f"₹{signal.get('ltp', 0):.2f}",                # ₹2379.80
            f"₹{signal.get('orb_high', 0):.2f}",           # ₹2368.00
            f"₹{signal.get('orb_low', 0):.2f}",            # ₹2347.20
            f"₹{signal.get('ema5', 0):.2f}",               # ₹2360.56
            signal.get('score', 0),                        # 45
            "🚀 AUTO-BUY"
        ]
        sheet.append_row(row)

    print(f"✅ {len(buy_signals)} BUY signals → Google Sheets @ {timestamp}")


def log_square_off(square_offs):
    """Log square-off events to Google Sheets"""
    if not square_offs:
        return

    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open("trade_log").sheet1
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    for so in square_offs:
        row = [
            timestamp,
            so.get('token', 'N/A'),
            so.get('symbol', 'UNKNOWN'),
            so.get('company_name', so.get('symbol', 'N/A')),
            f"₹{so.get('exit_price', 0):.2f}",
            f"₹{so.get('entry_price', 0):.2f}",
            f"{so.get('pct_change', 0):.2f}%",
            so.get('reason', ''),
            '',
            "🔻 SQUARE-OFF"
        ]
        sheet.append_row(row)

    print(f"✅ {len(square_offs)} SQUARE-OFF(s) → Google Sheets @ {timestamp}")
