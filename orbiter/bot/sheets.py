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

CONTROL_HEADER = ["Key", "Value"]
SYMBOLS_HEADER = ["Symbol", "Token", "Enabled"]
LEGACY_CONTROL_HEADER = ["Symbol", "Token", "Key", "Value"]


def _ensure_header(sheet, header):
    existing = sheet.row_values(1)
    if existing:
        return
    sheet.insert_row(header, 1)


def _get_or_create_worksheet(book, title):
    try:
        return book.worksheet(title)
    except Exception:
        return book.add_worksheet(title=title, rows="1000", cols="20")


def _parse_value(raw):
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered in ("true", "yes", "y", "1"):
        return True
    if lowered in ("false", "no", "n", "0"):
        return False
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text


def get_runtime_config(sheet_name="trade_log", config_tab="control", symbols_tab="symbols", ensure_headers=True):
    """Load runtime config and symbol list from Google Sheets."""
    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    client = gspread.authorize(creds)
    book = client.open(sheet_name)
    config_sheet = _get_or_create_worksheet(book, config_tab)
    symbols_sheet = _get_or_create_worksheet(book, symbols_tab)
    if ensure_headers:
        _ensure_header(config_sheet, CONTROL_HEADER)
        _ensure_header(symbols_sheet, SYMBOLS_HEADER)

    rows = config_sheet.get_all_values()
    config = {}
    header = rows[0] if rows else []
    is_legacy = header[:4] == LEGACY_CONTROL_HEADER
    if is_legacy:
        migrated = []
        for row in rows[1:]:
            key = row[2].strip() if len(row) > 2 else ""
            value = row[3].strip() if len(row) > 3 else ""
            if key:
                migrated.append([key, value])
        config_sheet.clear()
        config_sheet.insert_row(CONTROL_HEADER, 1)
        if migrated:
            config_sheet.append_rows(migrated)
        rows = config_sheet.get_all_values()
        header = rows[0] if rows else []
        is_legacy = False
    for row in rows[1:]:
        if is_legacy:
            key = row[2].strip() if len(row) > 2 else ""
            value = row[3].strip() if len(row) > 3 else ""
        else:
            key = row[0].strip() if len(row) > 0 else ""
            value = row[1].strip() if len(row) > 1 else ""
        if key:
            config[key] = _parse_value(value)

    symbols = []
    sym_rows = symbols_sheet.get_all_values()
    for row in sym_rows[1:]:
        symbol = row[0].strip() if len(row) > 0 else ""
        token = row[1].strip() if len(row) > 1 else ""
        enabled_raw = row[2].strip() if len(row) > 2 else ""
        enabled = _parse_value(enabled_raw)
        if enabled is None:
            enabled = True
        if token or symbol:
            symbols.append({"symbol": symbol, "token": token, "enabled": enabled})

    return {"config": config, "symbols": symbols}


def seed_runtime_config(sheet_name, config_tab, symbols_tab, default_config, symbols_list):
    """Seed empty control/symbols sheets with defaults."""
    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    client = gspread.authorize(creds)
    book = client.open(sheet_name)

    config_sheet = _get_or_create_worksheet(book, config_tab)
    _ensure_header(config_sheet, CONTROL_HEADER)
    config_rows = config_sheet.get_all_values()
    config_has_data = False
    for row in config_rows[1:]:
        if len(row) >= 2 and (row[0].strip() or row[1].strip()):
            config_has_data = True
            break
    if not config_has_data and default_config:
        rows = [[k, str(v)] for k, v in default_config.items()]
        config_sheet.append_rows(rows)

    symbols_sheet = _get_or_create_worksheet(book, symbols_tab)
    _ensure_header(symbols_sheet, SYMBOLS_HEADER)
    symbol_rows = symbols_sheet.get_all_values()
    symbols_has_data = False
    for row in symbol_rows[1:]:
        if len(row) >= 2 and (row[0].strip() or row[1].strip()):
            symbols_has_data = True
            break
    if not symbols_has_data and symbols_list:
        rows = []
        for item in symbols_list:
            if isinstance(item, dict):
                symbol = (item.get("symbol") or "").strip().upper()
                token = (item.get("token") or "").strip()
            else:
                symbol = ""
                token = str(item).strip()
            rows.append([symbol, token, "TRUE"])
        symbols_sheet.append_rows(rows)

def log_buy_signals(buy_signals):
    """Log ONLY 45pt+ BUY trades to Google Sheets with symbol and company name"""
    if not buy_signals:
        return

    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    client = gspread.authorize(creds)
    book = client.open("trade_log")
    sheet = _get_or_create_worksheet(book, "trade_log")
    _ensure_header(sheet, TRADE_LOG_HEADER)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    rows = []
    for signal in buy_signals:
        # ✅ Match new TRADE_LOG_HEADER
        row = [
            timestamp,
            signal.get('token', 'N/A'),
            signal.get('symbol', 'UNKNOWN'),
            signal.get('company_name', 'N/A'),
            "🚀 AUTO-BUY",
            f"₹{signal.get('ltp', 0):.2f}",                # Price
            f"₹{signal.get('ltp', 0):.2f}",                # Entry Price
            "0.00%",                                       # PnL %
            "₹0.00",                                       # PnL Per Share (₹)
            "₹0.00",                                       # Total PnL (₹)
            signal.get('score', 0),                        # Score
            f"₹{signal.get('orb_high', 0):.2f}",           # ORB High
            f"₹{signal.get('orb_low', 0):.2f}",            # ORB Low
            f"₹{signal.get('ema5', 0):.2f}",               # EMA5
            "Signal Confirmed",                            # Reason
            signal.get('strategy', ''),
            signal.get('expiry', ''),
            signal.get('atm_strike', ''),
            signal.get('hedge_strike', ''),
            signal.get('atm_symbol', ''),
            signal.get('hedge_symbol', ''),
            "YES" if signal.get('dry_run') else "NO",
            f"₹{signal.get('atm_premium_entry', 0):.2f}" if signal.get('atm_premium_entry') is not None else "",
            f"₹{signal.get('hedge_premium_entry', 0):.2f}" if signal.get('hedge_premium_entry') is not None else "",
            "",
            "",
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
        sheet.append_rows(rows)

    print(f"✅ {len(buy_signals)} BUY signals → Google Sheets @ {timestamp}")


def log_square_off(square_offs):
    """Log square-off events to Google Sheets"""
    if not square_offs:
        return

    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    client = gspread.authorize(creds)
    book = client.open("trade_log")
    sheet = _get_or_create_worksheet(book, "trade_log")
    _ensure_header(sheet, TRADE_LOG_HEADER)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    rows = []
    for so in square_offs:
        # ✅ Calculate Realized PnL: (Entry Spread) - (Exit Spread)
        atm_entry = float(so.get('atm_premium_entry', 0) or 0)
        hedge_entry = float(so.get('hedge_premium_entry', 0) or 0)
        atm_exit = float(so.get('atm_premium_exit', 0) or 0)
        hedge_exit = float(so.get('hedge_premium_exit', 0) or 0)
        lot_size = int(so.get('lot_size', 0) or 0)
        
        pnl_per_share = (atm_entry - hedge_entry) - (atm_exit - hedge_exit)
        total_pnl = pnl_per_share * lot_size

        # ✅ Match new TRADE_LOG_HEADER
        row = [
            timestamp,
            so.get('token', 'N/A'),
            so.get('symbol', 'UNKNOWN'),
            so.get('company_name', 'N/A'),
            "🔻 SQUARE-OFF",
            f"₹{so.get('exit_price', 0):.2f}",             # Price (Exit)
            f"₹{so.get('entry_price', 0):.2f}",            # Entry Price
            f"{so.get('pct_change', 0):.2f}%",             # PnL %
            f"₹{pnl_per_share:.2f}",                       # PnL Per Share (₹)
            f"₹{total_pnl:.2f}",                           # Total PnL (₹)
            "",                                            # Score (N/A)
            "",                                            # ORB High (N/A)
            "",                                            # ORB Low (N/A)
            "",                                            # EMA5 (N/A)
            so.get('reason', ''),                          # Reason
            so.get('strategy', ''),
            so.get('expiry', ''),
            so.get('atm_strike', ''),
            so.get('hedge_strike', ''),
            so.get('atm_symbol', ''),
            so.get('hedge_symbol', ''),
            "",
            f"₹{so.get('atm_premium_entry', 0):.2f}" if so.get('atm_premium_entry') is not None else "",
            f"₹{so.get('hedge_premium_entry', 0):.2f}" if so.get('hedge_premium_entry') is not None else "",
            f"₹{so.get('atm_premium_exit', 0):.2f}" if so.get('atm_premium_exit') is not None else "",
            f"₹{so.get('hedge_premium_exit', 0):.2f}" if so.get('hedge_premium_exit') is not None else "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            ""
        ]
        rows.append(row)
    
    if rows:
        sheet.append_rows(rows)

    print(f"✅ {len(square_offs)} SQUARE-OFF(s) → Google Sheets @ {timestamp}")


def log_scan_metrics(metrics):
    """Log per-scan symbol metrics (ORB/EMA) to Google Sheets."""
    if not metrics:
        return

    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    client = gspread.authorize(creds)
    book = client.open("trade_log")
    sheet = _get_or_create_worksheet(book, "scan_metrics")
    _ensure_header(sheet, SCAN_METRICS_HEADER)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")

    header = sheet.row_values(1)
    if not header:
        sheet.insert_row(SCAN_METRICS_HEADER, 1)
        header = SCAN_METRICS_HEADER
    else:
        missing = [col for col in SCAN_METRICS_HEADER if col not in header]
        if missing:
            last_col = _col_letter(len(SCAN_METRICS_HEADER))
            sheet.update(f"A1:{last_col}1", [SCAN_METRICS_HEADER])
            header = SCAN_METRICS_HEADER

    def _col_letter(index):
        letters = ""
        while index > 0:
            index, remainder = divmod(index - 1, 26)
            letters = chr(65 + remainder) + letters
        return letters

    token_col_idx = header.index("Token") + 1 if "Token" in header else 2
    all_data = sheet.get_all_values()
    token_rows = {row[token_col_idx-1]: i+1 for i, row in enumerate(all_data) if i > 0 and len(row) >= token_col_idx}

    updates = []
    new_rows = []

    for item in metrics:
        filters_payload = item.get('filters') or {}
        orb = filters_payload.get('ef1_orb', {}) if isinstance(filters_payload.get('ef1_orb', {}), dict) else {}
        ema = filters_payload.get('ef2_price_above_5ema', {}) if isinstance(filters_payload.get('ef2_price_above_5ema', {}), dict) else {}
        f3 = filters_payload.get('ef3_5ema_above_9ema', {}) if isinstance(filters_payload.get('ef3_5ema_above_9ema', {}), dict) else {}
        f4 = filters_payload.get('ef4_supertrend', {}) if isinstance(filters_payload.get('ef4_supertrend', {}), dict) else {}

        values = {
            "Timestamp": timestamp,
            "Token": item.get('token', 'N/A'),
            "Symbol": item.get('symbol', 'UNKNOWN'),
            "Company": item.get('company_name', item.get('symbol', 'N/A')),
            "Day Open": f"₹{item.get('day_open', 0):.2f}" if item.get('day_open') is not None else "",
            "Day High": f"₹{item.get('day_high', 0):.2f}" if item.get('day_high') is not None else "",
            "Day Low": f"₹{item.get('day_low', 0):.2f}" if item.get('day_low') is not None else "",
            "Day Close": f"₹{item.get('day_close', 0):.2f}" if item.get('day_close') is not None else "",
            "ORB Open": f"₹{orb.get('orb_open', 0):.2f}" if orb.get('orb_open') is not None else "",
            "EMA5": f"₹{ema.get('ema5', 0):.2f}" if ema.get('ema5') is not None else "",
            "ORB High": f"₹{orb.get('orb_high', 0):.2f}" if orb.get('orb_high') is not None else "",
            "ORB Low": f"₹{orb.get('orb_low', 0):.2f}" if orb.get('orb_low') is not None else "",
            "LTP": f"₹{item.get('ltp', 0):.2f}" if item.get('ltp') is not None else "",
            "Trade Taken": "YES" if item.get('trade_taken') else "NO",
            "SPAN PE": f"₹{item.get('span_pe', 0):.2f}" if item.get('span_pe') is not None else "",
            "Exposure PE": f"₹{item.get('expo_pe', 0):.2f}" if item.get('expo_pe') is not None else "",
            "Total Margin PE": f"₹{item.get('total_margin_pe', 0):.2f}" if item.get('total_margin_pe') is not None else "",
            "Pledged Required PE": f"₹{item.get('pledged_required_pe', 0):.2f}" if item.get('pledged_required_pe') is not None else "",
            "SPAN Trade PE": f"₹{item.get('span_trade_pe', 0):.2f}" if item.get('span_trade_pe') is not None else "",
            "Exposure Trade PE": f"₹{item.get('expo_trade_pe', 0):.2f}" if item.get('expo_trade_pe') is not None else "",
            "Pre Trade PE": f"₹{item.get('pre_trade_pe', 0):.2f}" if item.get('pre_trade_pe') is not None else "",
            "Add PE": f"₹{item.get('add_pe', 0):.2f}" if item.get('add_pe') is not None else "",
            "Add Trade PE": f"₹{item.get('add_trade_pe', 0):.2f}" if item.get('add_trade_pe') is not None else "",
            "Ten PE": f"₹{item.get('ten_pe', 0):.2f}" if item.get('ten_pe') is not None else "",
            "Ten Trade PE": f"₹{item.get('ten_trade_pe', 0):.2f}" if item.get('ten_trade_pe') is not None else "",
            "Del PE": f"₹{item.get('del_pe', 0):.2f}" if item.get('del_pe') is not None else "",
            "Del Trade PE": f"₹{item.get('del_trade_pe', 0):.2f}" if item.get('del_trade_pe') is not None else "",
            "Spl PE": f"₹{item.get('spl_pe', 0):.2f}" if item.get('spl_pe') is not None else "",
            "Spl Trade PE": f"₹{item.get('spl_trade_pe', 0):.2f}" if item.get('spl_trade_pe') is not None else "",

            "SPAN CE": f"₹{item.get('span_ce', 0):.2f}" if item.get('span_ce') is not None else "",
            "Exposure CE": f"₹{item.get('expo_ce', 0):.2f}" if item.get('expo_ce') is not None else "",
            "Total Margin CE": f"₹{item.get('total_margin_ce', 0):.2f}" if item.get('total_margin_ce') is not None else "",
            "Pledged Required CE": f"₹{item.get('pledged_required_ce', 0):.2f}" if item.get('pledged_required_ce') is not None else "",
            "SPAN Trade CE": f"₹{item.get('span_trade_ce', 0):.2f}" if item.get('span_trade_ce') is not None else "",
            "Exposure Trade CE": f"₹{item.get('expo_trade_ce', 0):.2f}" if item.get('expo_trade_ce') is not None else "",
            "Pre Trade CE": f"₹{item.get('pre_trade_ce', 0):.2f}" if item.get('pre_trade_ce') is not None else "",
            "Add CE": f"₹{item.get('add_ce', 0):.2f}" if item.get('add_ce') is not None else "",
            "Add Trade CE": f"₹{item.get('add_trade_ce', 0):.2f}" if item.get('add_trade_ce') is not None else "",
            "Ten CE": f"₹{item.get('ten_ce', 0):.2f}" if item.get('ten_ce') is not None else "",
            "Ten Trade CE": f"₹{item.get('ten_trade_ce', 0):.2f}" if item.get('ten_trade_ce') is not None else "",
            "Del CE": f"₹{item.get('del_ce', 0):.2f}" if item.get('del_ce') is not None else "",
            "Del Trade CE": f"₹{item.get('del_trade_ce', 0):.2f}" if item.get('del_trade_ce') is not None else "",
            "Spl CE": f"₹{item.get('spl_ce', 0):.2f}" if item.get('spl_ce') is not None else "",
            "Spl Trade CE": f"₹{item.get('spl_trade_ce', 0):.2f}" if item.get('spl_trade_ce') is not None else "",

            "F1 Score": orb.get('score', 0),
            "F2 Score": ema.get('score', 0),
            "F3 Score": f3.get('score', 0),
            "F4 Score": f4.get('score', 0)
        }

        def safe_float(val):
            if val is None:
                return ''
            if isinstance(val, float) and math.isnan(val):
                return 0.0  # Or '' or 'N/A'
            return val

        # After building values dict, clean it:
        clean_values = {k: safe_float(v) for k, v in values.items()}
        row = [clean_values.get(col, '') for col in header]

        token = item.get('token')
        if token in token_rows:
            row_idx = token_rows[token]
            last_col = _col_letter(len(header))
            updates.append({
                'range': f"A{row_idx}:{last_col}{row_idx}",
                'values': [row]
            })
        else:
            new_rows.append(row)

    print(f"✅ {len(metrics)} scan metrics → Google Sheets @ {timestamp}")


def update_active_positions(active_data):
    """Rewrite the 'active_positions' sheet with real-time data"""
    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    client = gspread.authorize(creds)
    book = client.open("trade_log")
    sheet = _get_or_create_worksheet(book, "active_positions")
    
    # Always reset header
    sheet.clear()
    sheet.insert_row(POSITIONS_HEADER, 1)
    
    if not active_data:
        return

    rows = []
    for item in active_data:
        row = [
            item.get('entry_time'),
            item.get('token'),
            item.get('symbol'),
            item.get('company_name'),
            f"₹{item.get('entry_price', 0):.2f}",
            f"₹{item.get('ltp', 0):.2f}",
            f"{item.get('pnl_pct', 0):.2f}%",
            f"₹{item.get('pnl_rs', 0):.2f}",
            f"{item.get('max_profit_pct', 0):.2f}%",
            f"₹{item.get('max_pnl_rs', 0):.2f}",
            item.get('strategy'),
            item.get('expiry'),
            item.get('atm_symbol'),
            item.get('hedge_symbol'),
            f"₹{item.get('total_margin', 0):.2f}"
        ]
        rows.append(row)
    
    if rows:
        sheet.append_rows(rows, value_input_option='USER_ENTERED')


def log_closed_positions(closed_data):
    """Append to 'closed_positions' and update overall PnL summary"""
    if not closed_data:
        return

    creds_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
    client = gspread.authorize(creds)
    book = client.open("trade_log")
    sheet = _get_or_create_worksheet(book, "closed_positions")
    _ensure_header(sheet, CLOSED_POSITIONS_HEADER)
    
    rows = []
    for so in closed_data:
        # Calculate Total PnL for row
        atm_entry = float(so.get('atm_premium_entry', 0) or 0)
        hedge_entry = float(so.get('hedge_premium_entry', 0) or 0)
        atm_exit = float(so.get('atm_premium_exit', 0) or 0)
        hedge_exit = float(so.get('hedge_premium_exit', 0) or 0)
        lot_size = int(so.get('lot_size', 0) or 0)
        
        pnl_per_share = (atm_entry - hedge_entry) - (atm_exit - hedge_exit)
        total_pnl = pnl_per_share * lot_size

        row = [
            so.get('entry_time'),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
            so.get('token'),
            so.get('symbol'),
            so.get('company_name'),
            f"₹{so.get('entry_price', 0):.2f}",
            f"₹{so.get('exit_price', 0):.2f}",
            f"{so.get('pct_change', 0):.2f}%",
            f"₹{pnl_per_share:.2f}",
            f"₹{total_pnl:.2f}",
            so.get('reason'),
            so.get('strategy'),
            so.get('expiry')
        ]
        rows.append(row)
    
    if rows:
        sheet.append_rows(rows, value_input_option='USER_ENTERED')
        
    print(f"✅ {len(closed_data)} positions logged to closed_positions")

