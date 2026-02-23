from datetime import datetime
import os
import json
import importlib.util
from typing import Dict, Any, List

class OrbiterState:
    def __init__(self, client, symbols: List[str], filters_module, config: Dict[str, Any], segment_name: str = 'nfo'):
        self.client = client
        self.symbols = symbols
        self.filters = filters_module
        self.config = config
        self.segment_name = segment_name.lower()
        
        # position_info = {'entry_price', 'entry_time', 'symbol', 'company_name', ...}
        self.active_positions = {}
        self.exit_history = {} # 🔥 Track last exit time for cooldowns
        self.opening_scores = {} # 🔥 Track first score of the day
        
        # 🔥 NEW: Global TSL State
        self.max_portfolio_pnl = 0.0
        self.global_tsl_active = False
        self.realized_pnl = 0.0
        self.trade_count = 0

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
            # Convert datetime objects to strings for JSON in both positions and history
            def json_serial(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                raise TypeError(f"Type {type(obj)} not serializable")

            # 🔥 Deep copy and sanitize active_positions to remove non-serializable objects
            sanitized_positions = {}
            for token, info in self.active_positions.items():
                pos_copy = info.copy()
                if 'config' in pos_copy: del pos_copy['config'] # 🔥 Remove non-serializable config
                sanitized_positions[token] = pos_copy

            data = {
                'last_updated': datetime.now().timestamp(),
                'active_positions': sanitized_positions,
                'exit_history': self.exit_history,
                'opening_scores': self.opening_scores,
                'max_portfolio_pnl': self.max_portfolio_pnl,
                'global_tsl_active': self.global_tsl_active,
                'realized_pnl': self.realized_pnl,
                'trade_count': self.trade_count
            }
            
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            tmp_file = self.state_file + ".tmp"
            with open(tmp_file, 'w') as f:
                json.dump(data, f, indent=4, default=json_serial)
            os.replace(tmp_file, self.state_file) # 🔥 Atomic Swap to prevent corruption
            
        except Exception as e:
            print(f"⚠️ Failed to save session: {e}")
            import traceback
            traceback.print_exc()

    def load_session(self):
        """Recover session from disk with freshness protocol"""
        if not os.path.exists(self.state_file):
            return

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"⚠️ Corrupted session file detected: {e}")
            backup_path = self.state_file + ".corrupt"
            try:
                os.replace(self.state_file, backup_path)
                print(f"💾 Corrupted file moved to {backup_path} for investigation.")
            except: pass
            return
        except Exception as e:
            print(f"⚠️ Failed to load session: {e}")
            return

        try:
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
            self.opening_scores = data.get('opening_scores', {})
            self.max_portfolio_pnl = data.get('max_portfolio_pnl', 0.0)
            self.global_tsl_active = data.get('global_tsl_active', False)
            self.realized_pnl = data.get('realized_pnl', 0.0)
            self.trade_count = data.get('trade_count', 0)
            
            if self.active_positions:
                print(f"🧠 Recovered {len(self.active_positions)} active positions from disk.")
        except Exception as e:
            print(f"⚠️ Failed to load session: {e}")
