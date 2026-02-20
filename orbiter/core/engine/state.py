from datetime import datetime
import os
import json
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
        self.exit_history = {} # 🔥 Track last exit time for cooldowns
        self.last_scan_metrics = []
        self.last_scan_log_ts = 0
        self.filter_results_cache = {}
        
        # Component references (to be set by Orbiter)
        self.evaluator = None
        self.executor = None
        self.syncer = None
        
        self.verbose_logs = self.config.get('VERBOSE_LOGS', False)
        
        # Initialize margin cache path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.client.set_span_cache_path(os.path.join(base_dir, 'data', 'span', 'cache.json'))
        self.client.load_span_cache()
        
        self.state_file = os.path.join(base_dir, 'data', 'session_state.json')

    def save_session(self):
        """Persist active positions and exit history to disk"""
        try:
            # Convert datetime objects to strings for JSON
            serializable_positions = {}
            for token, info in self.active_positions.items():
                pos_copy = info.copy()
                if isinstance(pos_copy.get('entry_time'), datetime):
                    pos_copy['entry_time'] = pos_copy['entry_time'].isoformat()
                serializable_positions[token] = pos_copy

            data = {
                'last_updated': datetime.now().timestamp(),
                'active_positions': serializable_positions,
                'exit_history': self.exit_history
            }
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"⚠️ Failed to save session: {e}")

    def load_session(self):
        """Recover session from disk with freshness protocol"""
        if not os.path.exists(self.state_file):
            return

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)

            # 1. Freshness Check (30 minutes expiry)
            last_ts = data.get('last_updated', 0)
            if (datetime.now().timestamp() - last_ts) > 1800:
                print("⚠️ Stale session file found (> 30m). Ignoring.")
                return

            # 2. Re-hydrate Positions
            raw_positions = data.get('active_positions', {})
            for token, info in raw_positions.items():
                if 'entry_time' in info:
                    info['entry_time'] = datetime.fromisoformat(info['entry_time'])
                self.active_positions[token] = info
            
            self.exit_history = data.get('exit_history', {})
            
            if self.active_positions:
                print(f"🧠 Recovered {len(self.active_positions)} active positions from disk.")
        except Exception as e:
            print(f"⚠️ Failed to load session: {e}")
