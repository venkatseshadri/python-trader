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
            
            # 🔥 NEW: Cloud Mirror (v3.14.0)
            if self.syncer:
                self.syncer.cloud_save_state(self)
                
        except Exception as e:
            print(f"⚠️ Failed to save session: {e}")
            import traceback
            traceback.print_exc()

    def load_session(self):
        """Recover session from disk or Cloud Snapshot (Google Sheets)"""
        data = None
        
        # 1. Try Local Load
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                
                # Freshness Check (30 minutes expiry)
                if (datetime.now().timestamp() - data.get('last_updated', 0)) > 1800:
                    print("⚠️ Local session stale (> 30m). Checking cloud...")
                    data = None
            except Exception as e:
                print(f"⚠️ Local load failed: {e}")
                data = None

        # 2. Try Cloud Load (v3.14.0)
        if not data and self.syncer:
            print("☁️ Attempting Cloud State recovery from Google Sheets...")
            cloud_json = self.syncer.cloud_load_state()
            if cloud_json:
                try:
                    data = json.loads(cloud_json)
                    print("✅ Cloud Snapshot recovered successfully.")
                except Exception as e:
                    print(f"⚠️ Cloud parsing failed: {e}")

        if not data:
            return

        try:
            # Re-hydrate Positions
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
                print(f"🧠 Recovered {len(self.active_positions)} positions (via {'Cloud' if not os.path.exists(self.state_file) else 'Disk'}).")
        except Exception as e:
            print(f"⚠️ Failed to re-hydrate session: {e}")


    def sync_with_broker(self):
        """
        🔥 BROKER SYNC (v3.13.6)
        Queries the broker for actual open positions and matches them with our universe.
        If a position is missing from internal state (e.g. handover), it is re-imported.
        """
        print("🔄 Syncing internal state with Broker API...")
        real_positions = self.client.get_positions()
        if not real_positions:
            print("✅ Broker reporting zero open positions.")
            return

        for p in real_positions:
            qty = int(p.get('netqty', 0))
            if qty == 0: continue
            
            token = f"{p['exch']}|{p['token']}"
            if token not in self.active_positions:
                # 🔥 FOUND A GHOST POSITION (Missing in state but live in broker)
                print(f"👻 Re-importing missing position: {p['tsym']} ({qty} lots)")
                
                # Reconstruct minimum required info for the engine to manage it
                self.active_positions[token] = {
                    "entry_price": float(p.get('avgprc', 0)),
                    "entry_time": datetime.now(), # Approximate
                    "symbol": p['tsym'],
                    "company_name": self.client.get_company_name(p['token'], exchange=p['exch']),
                    "strategy": "FUTURE_LONG" if qty > 0 else "FUTURE_SHORT",
                    "lot_size": abs(qty),
                    "total_margin": 50000.0, # Reset to safe default
                    "regime": "SIDEWAYS",
                    "tp_trail_activation": 1.5,
                    "tp_trail_gap": 0.75,
                    "pnl_rs": float(p.get('rpnl', 0)) + float(p.get('urpnl', 0))
                }
        
        print(f"✅ Handover complete. Managing {len(self.active_positions)} total positions.")

