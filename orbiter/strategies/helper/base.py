from datetime import datetime
import os
import importlib.util
import filters
from config.config import VERBOSE_LOGS

# Load sheets.py dynamically from bot/ folder
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sheets_path = os.path.join(base_dir, "bot", "sheets.py")

try:
    spec = importlib.util.spec_from_file_location("sheets", sheets_path)
    sheets = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sheets)
    log_buy_signals = sheets.log_buy_signals
    log_scan_metrics = getattr(sheets, 'log_scan_metrics', None)
    update_active_positions = getattr(sheets, 'update_active_positions', None)
    log_closed_positions = getattr(sheets, 'log_closed_positions', None)
except Exception as e:
    print(f"⚠️ Warning: Could not load sheets.py: {e}")
    log_buy_signals = lambda x: print(f"📝 [Mock] Buy Signal: {x}")
    log_scan_metrics = lambda x: None
    update_active_positions = lambda x: None
    log_closed_positions = lambda x: None

# SL/TP filters - generic registry from filters package
SL_FILTERS = getattr(filters, 'get_filters', lambda _: [])('sl')
TP_FILTERS = getattr(filters, 'get_filters', lambda _: [])('tp')

class OrbiterState:
    def __init__(self, client, symbols, filters_module, config):
        self.client = client
        self.symbols = symbols
        self.filters = filters_module
        self.config = config
        
        # info = {'entry_price': float, 'entry_time': datetime, 'symbol': str, 'company_name': str, ...}
        self.active_positions = {}
        self.last_scan_metrics = []
        self.last_scan_log_ts = 0
        self.filter_results_cache = {}
        
        self.verbose_logs = self.config.get('VERBOSE_LOGS', VERBOSE_LOGS)
        
        # Initialize margin cache path
        self.client.set_span_cache_path(os.path.join(base_dir, 'data', 'span', 'cache.json'))
        self.client.load_span_cache()
