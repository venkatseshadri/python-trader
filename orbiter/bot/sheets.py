import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import os
import json

SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

TRADE_LOG_HEADER = [
    "Timestamp", "Token", "Symbol", "Company", "LTP", "ORB High", "ORB Low", "EMA5",
    "Score", "Action", "Strategy", "Expiry", "ATM Strike", "Hedge Strike",
    "ATM Symbol", "Hedge Symbol", "Dry Run",
    "ATM Premium Entry", "Hedge Premium Entry", "ATM Premium Exit", "Hedge Premium Exit"
]

SCAN_METRICS_HEADER = [
    "Timestamp", "Token", "Symbol", "Company", "Day Open", "Day High", "Day Low",
    "Day Close", "ORB Open", "EMA5", "ORB High", "ORB Low", "LTP", "Trade Taken",
    "SPAN PE", "Exposure PE", "Total Margin PE", "Pledged Required PE",
    "SPAN CE", "Exposure CE", "Total Margin CE", "Pledged Required CE",
    "F1 Score", "F2 Score", "F3 Score", "F4 Score"
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
            "🚀 AUTO-BUY",
            signal.get('strategy', ''),
            signal.get('expiry', ''),
            signal.get('atm_strike', ''),
            signal.get('hedge_strike', ''),
            signal.get('atm_symbol', ''),
            signal.get('hedge_symbol', ''),
            "YES" if signal.get('dry_run') else "",
            f"₹{signal.get('atm_premium_entry', 0):.2f}" if signal.get('atm_premium_entry') is not None else "",
            f"₹{signal.get('hedge_premium_entry', 0):.2f}" if signal.get('hedge_premium_entry') is not None else "",
            "",
            ""
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
    book = client.open("trade_log")
    sheet = _get_or_create_worksheet(book, "trade_log")
    _ensure_header(sheet, TRADE_LOG_HEADER)
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
            "🔻 SQUARE-OFF",
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
            f"₹{so.get('hedge_premium_exit', 0):.2f}" if so.get('hedge_premium_exit') is not None else ""
        ]
        sheet.append_row(row)

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
    token_rows = sheet.col_values(token_col_idx)

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
            "SPAN CE": f"₹{item.get('span_ce', 0):.2f}" if item.get('span_ce') is not None else "",
            "Exposure CE": f"₹{item.get('expo_ce', 0):.2f}" if item.get('expo_ce') is not None else "",
            "Total Margin CE": f"₹{item.get('total_margin_ce', 0):.2f}" if item.get('total_margin_ce') is not None else "",
            "Pledged Required CE": f"₹{item.get('pledged_required_ce', 0):.2f}" if item.get('pledged_required_ce') is not None else "",
            "F1 Score": orb.get('score', 0),
            "F2 Score": ema.get('score', 0),
            "F3 Score": f3.get('score', 0),
            "F4 Score": f4.get('score', 0)
        }

        row = [values.get(col, "") for col in header]

        token = item.get('token')
        row_indexes = [idx + 1 for idx, value in enumerate(token_rows) if idx >= 1 and value == token]
        if row_indexes:
            for row_idx in row_indexes:
                last_col = _col_letter(len(header))
                sheet.update(f"A{row_idx}:{last_col}{row_idx}", [row])
        else:
            sheet.append_row(row)
            token_rows.append(token)

    print(f"✅ {len(metrics)} scan metrics → Google Sheets @ {timestamp}")
