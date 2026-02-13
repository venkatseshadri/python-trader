from datetime import datetime
import os
import importlib.util
from typing import Dict, Any, List

class OrbiterState:
    def __init__(self, client, symbols: List[str], filters_module, config: Dict[str, Any]):
        self.client = client
        self.symbols = symbols
        self.filters = filters_module
        self.config = config
        
        # position_info = {'entry_price', 'entry_time', 'symbol', 'company_name', ...}
        self.active_positions = {}
        self.last_scan_metrics = []
        self.last_scan_log_ts = 0
        self.filter_results_cache = {}
        
        # Component references (to be set by Orbiter)
        self.evaluator = None
        self.executor = None
        self.syncer = None
        
        self.verbose_logs = self.config.get('VERBOSE_LOGS', False)
        
        # Initialize segment-specific margin cache path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        seg_name = self.config.get('segment_name', 'nfo').lower()
        cache_file = f"{seg_name}_span_cache.json"
        self.client.set_span_cache_path(os.path.join(base_dir, 'data', 'span', cache_file))
        self.client.load_span_cache()
