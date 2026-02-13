import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json
import math

SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

TRADE_LOG_HEADER = [
    "Timestamp", "Token", "Symbol", "Company", "Action", "Price", "Entry Price", "PnL %", 
    "PnL Per Share (₹)", "Total PnL (₹)",
    "Score", "ORB High", "ORB Low", "EMA5", "Reason", "Strategy", "Expiry", 
    "ATM Strike", "Hedge Strike", "ATM Symbol", "Hedge Symbol", "Dry Run",
    "ATM Premium Entry", "Hedge Premium Entry", "ATM Premium Exit", "Hedge Premium Exit",
    "SPAN", "Exposure", "Total Margin", "Pledged Required",
    "SPAN Trade", "Exposure Trade", "Pre Trade", "Add", "Add Trade", "Ten", "Ten Trade", "Del", "Del Trade", "Spl", "Spl Trade"
]

POSITIONS_HEADER = [
    "Entry Timestamp", "Token", "Symbol", "Company", "Entry Price", "LTP", "Current PnL %", "Current PnL (₹)", 
    "Max Profit %", "Max PnL (₹)", "Strategy", "Expiry", "ATM Symbol", "Hedge Symbol", "Total Margin"
]

CLOSED_POSITIONS_HEADER = [
    "Entry Timestamp", "Exit Timestamp", "Token", "Symbol", "Company", "Entry Price", "Exit Price", 
    "PnL %", "PnL Per Share (₹)", "Total PnL (₹)", "Reason", "Strategy", "Expiry"
]

SCAN_METRICS_HEADER = [
    "Timestamp", "Token", "Symbol", "Company", "Day Open", "Day High", "Day Low",
    "Day Close", "ORB Open", "EMA5", "ORB High", "ORB Low", "LTP", "Trade Taken",
    "F1 Score", "F2 Score", "F3 Score", "F4 Score",
    "SPAN PE", "Exposure PE", "Total Margin PE", "Pledged Required PE",
    "SPAN Trade PE", "Exposure Trade PE", "Pre Trade PE", "Add PE", "Add Trade PE", "Ten PE", "Ten Trade PE", "Del PE", "Del Trade PE", "Spl PE", "Spl Trade PE",
    "SPAN CE", "Exposure CE", "Total Margin CE", "Pledged Required CE",
    "SPAN Trade CE", "Exposure Trade CE", "Pre Trade CE", "Add CE", "Add Trade CE", "Ten CE", "Ten Trade CE", "Del CE", "Del Trade CE", "Spl CE", "Spl Trade CE"
]

def _get_gsheet_client():
    """Centralized authentication for Google Sheets"""
    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    return gspread.authorize(creds)

def _ensure_header(sheet, header):
    existing = sheet.row_values(1)
    if not existing:
        sheet.insert_row(header, 1)

def _get_or_create_worksheet(book, title):
    try:
        return book.worksheet(title)
    except Exception:
        return book.add_worksheet(title=title, rows="1000", cols="45")

def safe_float(val):
    if val is None: return 0.0
    try: return float(str(val).replace('₹', '').replace(',', '').strip())
    except (ValueError, TypeError): return 0.0

def log_buy_signals(buy_signals, segment_name=None):
    """Log BUY trades to segment-specific trade_log sheet"""
    if not buy_signals or not segment_name: return
    
    client = _get_gsheet_client()
    book = client.open("trade_log")
    sheet = _get_or_create_worksheet(book, f"trade_log_{segment_name.lower()}")
    _ensure_header(sheet, TRADE_LOG_HEADER)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    rows = []
    for signal in buy_signals:
        row = [
            timestamp,
            signal.get('token', 'N/A'),
            signal.get('symbol', 'UNKNOWN'),
            signal.get('company_name', 'N/A'),
            "🚀 AUTO-BUY",
            f"₹{signal.get('ltp', 0):.2f}",
            f"₹{signal.get('ltp', 0):.2f}",
            "0.00%", "₹0.00", "₹0.00",
            signal.get('score', 0),
            f"₹{signal.get('orb_high', 0):.2f}",
            f"₹{signal.get('orb_low', 0):.2f}",
            f"₹{signal.get('ema5', 0):.2f}",
            "Signal Confirmed",
            signal.get('strategy', ''),
            signal.get('expiry', ''),
            signal.get('atm_strike', ''),
            signal.get('hedge_strike', ''),
            signal.get('atm_symbol', ''),
            signal.get('hedge_symbol', ''),
            "YES" if signal.get('dry_run') else "NO",
            f"₹{signal.get('atm_premium_entry', 0):.2f}" if signal.get('atm_premium_entry') is not None else "",
            f"₹{signal.get('hedge_premium_entry', 0):.2f}" if signal.get('hedge_premium_entry') is not None else "",
            "", "",
            f"₹{signal.get('span', 0):.2f}",
            f"₹{signal.get('expo', 0):.2f}",
            f"₹{signal.get('total_margin', 0):.2f}",
            f"₹{signal.get('pledged_required', 0):.2f}",
            f"₹{signal.get('span_trade', 0):.2f}",
            f"₹{signal.get('expo_trade', 0):.2f}",
            f"₹{signal.get('pre_trade', 0):.2f}",
            f"₹{signal.get('add', 0):.2f}",
            f"₹{signal.get('add_trade', 0):.2f}",
            f"₹{signal.get('ten', 0):.2f}",
            f"₹{signal.get('ten_trade', 0):.2f}",
            f"₹{signal.get('del', 0):.2f}",
            f"₹{signal.get('del_trade', 0):.2f}",
            f"₹{signal.get('spl', 0):.2f}",
            f"₹{signal.get('spl_trade', 0):.2f}"
        ]
        rows.append(row)
    
    if rows:
        sheet.append_rows(rows, value_input_option='USER_ENTERED')
    print(f"✅ {len(buy_signals)} BUY signals logged to trade_log_{segment_name}")

def log_closed_positions(closed_data, segment_name=None):
    """Log closed trades and update shared summary PnL"""
    if not closed_data or not segment_name: return
    
    client = _get_gsheet_client()
    book = client.open("trade_log")
    sheet = _get_or_create_worksheet(book, f"closed_positions_{segment_name.lower()}")
    _ensure_header(sheet, CLOSED_POSITIONS_HEADER)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
    
    rows, total_batch_pnl = [], 0.0
    from utils.utils import safe_float
    for so in closed_data:
        atm_entry = safe_float(so.get('atm_premium_entry'))
        hedge_entry = safe_float(so.get('hedge_premium_entry'))
        atm_exit = safe_float(so.get('atm_premium_exit'))
        hedge_exit = safe_float(so.get('hedge_premium_exit'))
        lot_size = int(so.get('lot_size', 0) or 0)
        
        pnl_per_share = (atm_entry - hedge_entry) - (atm_exit - hedge_exit)
        total_pnl = pnl_per_share * lot_size
        total_batch_pnl += total_pnl

        rows.append([
            so.get('entry_time'), timestamp, so.get('token'), so.get('symbol'), so.get('company_name'),
            f"₹{safe_float(so.get('entry_price')):.2f}", f"₹{safe_float(so.get('exit_price')):.2f}",
            f"{safe_float(so.get('pct_change')):.2f}%", f"₹{pnl_per_share:.2f}", f"₹{total_pnl:.2f}",
            so.get('reason'), so.get('strategy'), so.get('expiry')
        ])
    
    if rows:
        sheet.append_rows(rows, value_input_option='USER_ENTERED')
        _update_summary_pnl(book, total_batch_pnl)
    print(f"✅ {len(closed_data)} positions logged to closed_positions_{segment_name}")

def _update_summary_pnl(book, amount):
    """Update global summary sheet across ALL segments"""
    sheet = _get_or_create_worksheet(book, "summary")
    _ensure_header(sheet, ["Date", "Overall Day PnL (₹)"])
    
    today = datetime.now().strftime("%Y-%m-%d")
    all_rows = sheet.get_all_values()
    
    row_idx = -1
    for i, row in enumerate(all_rows):
        if i > 0 and row[0] == today:
            row_idx = i + 1
            break
            
    if row_idx != -1:
        current_val = safe_float(all_rows[row_idx-1][1])
        new_val = current_val + amount
        sheet.update_cell(row_idx, 2, f"₹{new_val:.2f}")
    else:
        sheet.append_row([today, f"₹{amount:.2f}"], value_input_option='USER_ENTERED')

def log_scan_metrics(metrics, segment_name=None):
    """Update segment-specific dashboard with live technicals"""
    if not metrics or not segment_name: return
    
    client = _get_gsheet_client()
    book = client.open("trade_log")
    sheet = _get_or_create_worksheet(book, f"scan_metrics_{segment_name.lower()}")
    _ensure_header(sheet, SCAN_METRICS_HEADER)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    header = sheet.row_values(1)
    def _col_letter(index):
        letters = ""
        while index > 0:
            index, remainder = divmod(index - 1, 26)
            letters = chr(65 + remainder) + letters
        return letters

    token_col_idx = header.index("Token") + 1 if "Token" in header else 2
    all_data = sheet.get_all_values()
    token_rows = {row[token_col_idx-1]: i+1 for i, row in enumerate(all_data) if i > 0 and len(row) >= token_col_idx}

    from utils.utils import safe_float

    def _fmt(val):
        num = safe_float(val, default=None)
        return f"₹{num:.2f}" if num is not None else ""

    updates, new_rows = [], []
    for item in metrics:
        f = item.get('filters') or {}
        orb = f.get('ef1_orb', {}) if isinstance(f.get('ef1_orb', {}), dict) else {}
        ema = f.get('ef2_price_above_5ema', {}) if isinstance(f.get('ef2_price_above_5ema', {}), dict) else {}
        f3 = f.get('ef3_5ema_above_9ema', {}) if isinstance(f.get('ef3_5ema_above_9ema', {}), dict) else {}
        f4 = f.get('ef4_supertrend', {}) if isinstance(f.get('ef4_supertrend', {}), dict) else {}

        # Build values mapping
        v = {
            "Timestamp": timestamp, "Token": item.get('token', 'N/A'), "Symbol": item.get('symbol', 'UNKNOWN'),
            "Company": item.get('company_name', item.get('symbol', 'N/A')),
            "Day Open": _fmt(item.get('day_open')),
            "Day High": _fmt(item.get('day_high')),
            "Day Low": _fmt(item.get('day_low')),
            "Day Close": _fmt(item.get('day_close')),
            "ORB Open": _fmt(orb.get('orb_open')),
            "EMA5": _fmt(ema.get('ema5')),
            "ORB High": _fmt(orb.get('orb_high')),
            "ORB Low": _fmt(orb.get('orb_low')),
            "LTP": _fmt(item.get('ltp')),
            "Trade Taken": "YES" if item.get('trade_taken') else "NO",
            "F1 Score": safe_float(orb.get('score', 0)), 
            "F2 Score": safe_float(ema.get('score', 0)), 
            "F3 Score": safe_float(f3.get('score', 0)), 
            "F4 Score": safe_float(f4.get('score', 0))
        }
        
        # Add Span details (FUT or PE/CE)
        sf = item.get('span_fut', {})
        if sf.get('ok'):
            v["SPAN PE"] = _fmt(sf.get('span'))
            v["Total Margin PE"] = _fmt(sf.get('total_margin'))
            v["Pledged Required PE"] = _fmt(sf.get('pledged_required'))
        else:
            for side in ['PE', 'CE']:
                s_data = item.get(f'span_{side.lower()}', {})
                if s_data.get('ok'):
                    v[f"SPAN {side}"] = _fmt(s_data.get('span'))
                    v[f"Exposure {side}"] = _fmt(s_data.get('expo'))
                    v[f"Total Margin {side}"] = _fmt(s_data.get('total_margin'))
                    v[f"Pledged Required {side}"] = _fmt(s_data.get('pledged_required'))
                    for key in ['span_trade', 'expo_trade', 'pre_trade', 'add', 'add_trade', 'ten', 'ten_trade', 'del', 'del_trade', 'spl', 'spl_trade']:
                        v[f"{key.replace('_', ' ').title()} {side}"] = _fmt(s_data.get(key))

        row = [v.get(col, '') for col in header]
        token = item.get('token')
        if token in token_rows:
            updates.append({'range': f"A{token_rows[token]}:{_col_letter(len(header))}{token_rows[token]}", 'values': [row]})
        else: new_rows.append(row)

    if updates: sheet.batch_update(updates, value_input_option='USER_ENTERED')
    if new_rows: sheet.append_rows(new_rows, value_input_option='USER_ENTERED')
    print(f"✅ {len(metrics)} scan metrics updated in scan_metrics_{segment_name}")

def update_active_positions(active_data, segment_name=None):
    """Live dashboard for segment positions"""
    if not segment_name: return
    client = _get_gsheet_client()
    book = client.open("trade_log")
    sheet = _get_or_create_worksheet(book, f"active_positions_{segment_name.lower()}")
    sheet.clear()
    sheet.insert_row(POSITIONS_HEADER, 1)
    
    if not active_data: return
    rows = []
    from utils.utils import safe_float
    def _fmt(val, is_pct=False):
        num = safe_float(val, default=None)
        if num is None: return ""
        return f"{num:.2f}%" if is_pct else f"₹{num:.2f}"

    for i in active_data:
        rows.append([
            i.get('entry_time'), i.get('token'), i.get('symbol'), i.get('company_name'),
            _fmt(i.get('entry_price')), _fmt(i.get('ltp')),
            _fmt(i.get('pnl_pct'), True), _fmt(i.get('pnl_rs')),
            _fmt(i.get('max_profit_pct'), True), _fmt(i.get('max_pnl_rs')),
            i.get('strategy'), i.get('expiry'), i.get('atm_symbol'), i.get('hedge_symbol'), _fmt(i.get('total_margin'))
        ])
    if rows: sheet.append_rows(rows, value_input_option='USER_ENTERED')
