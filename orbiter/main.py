#!/usr/bin/env python3
"""
🚀 ORBITER v3.0 - Unified Segment Multi-Market Trader
"""

import time
import sys
import os
import argparse
import pytz
from datetime import datetime, time as dt_time

# Path setup
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, base_dir)
sys.path.append(os.path.join(base_dir, '..', 'ShoonyaApi-py'))

from core.client import BrokerClient
from core.engine.state import OrbiterState
from core.engine.evaluator import Evaluator
from core.engine.executor import Executor
from core.engine.syncer import Syncer
import filters
import config.main_config as main_config

class Orbiter:
    def __init__(self, exchange_override: str = None, simulation: bool = False):
        self.simulation = simulation
        self.exchange_override = exchange_override.lower() if exchange_override else None
        self.client = None
        self.state = None
        self.evaluator = Evaluator()
        self.executor = None
        self.syncer = None

    def _get_active_segment(self):
        """Detect or override the active segment (NFO or MCX)"""
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist)
        current_time = now.time()
        
        # Import configs
        import config.nfo.exchange_config as nfo
        import config.mcx.exchange_config as mcx
        
        # 1. Determine Segment
        if self.exchange_override:
            if self.exchange_override == 'nfo':
                print("☀️ Manual override: Loading NFO Segment")
                segment = nfo
            elif self.exchange_override == 'mcx':
                print("🌙 Manual override: Loading MCX Segment")
                segment = mcx
            else:
                raise ValueError(f"❌ Invalid exchange '{self.exchange_override}'. Must be 'nfo' or 'mcx'.")
        else:
            # Time-based detection
            if current_time > nfo.MARKET_CLOSE:
                print("🌙 Evening session: Detected MCX time window")
                segment = mcx
            else:
                print("☀️ Day session: Detected NFO time window")
                segment = nfo

        # 2. Segment-Specific Holiday/Off-Hours Check
        is_weekend = now.weekday() >= 5
        is_holiday = now.strftime("%Y-%m-%d") in segment.MARKET_HOLIDAYS
        is_off_hours = not (segment.MARKET_OPEN <= current_time <= segment.MARKET_CLOSE)
        
        if not self.simulation:
            if is_weekend or is_holiday or is_off_hours:
                reason = "WEEKEND" if is_weekend else ("HOLIDAY" if is_holiday else "OFF-HOURS")
                print(f"😴 {reason} for active segment! Soft-enabling SIMULATION mode.")
                self.simulation = True
            else:
                seg_name = "MCX" if segment == mcx else "NFO"
                print(f"🟢 Market is LIVE for {seg_name}")

        return segment

    def setup(self):
        print("✅ Initializing Engine...")
        try:
            segment = self._get_active_segment()
        except ValueError as e:
            print(e)
            sys.exit(1)

        # Extract segment name (nfo or mcx) from config module name
        seg_name = segment.__name__.split('.')[-2]
        
        # ✅ Build merged configuration (Strategy + Full Segment Overrides)
        full_config = vars(main_config).copy()
        segment_vars = {k: v for k, v in vars(segment).items() if not k.startswith('__')}
        full_config.update(segment_vars)
        
        # Add runtime context
        full_config['segment_name'] = seg_name
        full_config['SIMULATION'] = self.simulation
        
        # Initialize Agnostic Components
        self.client = BrokerClient("../ShoonyaApi-py/cred.yml", segment_name=seg_name)
        self.state = OrbiterState(self.client, segment.SYMBOLS_FUTURE_UNIVERSE, filters, full_config)
        
        # Inject agnostic sheets logic
        from bot.sheets import log_buy_signals, log_closed_positions, update_active_positions
        from filters import get_filters
        
        self.executor = Executor(log_buy_signals, log_closed_positions, get_filters('sl'), get_filters('tp'))
        self.syncer = Syncer(update_active_positions)
        
        # Link state back to components
        self.state.evaluator = self.evaluator
        self.state.executor = self.executor
        self.state.syncer = self.syncer

        print(f"📊 Universe: {len(segment.SYMBOLS_FUTURE_UNIVERSE)} tokens")
        print(f"🎯 Entry Threshold: {full_config['TRADE_SCORE']}pts")

    def login(self):
        ok = self.client.login()
        if not ok: return False
        self.client.start_live_feed(self.state.symbols)
        return True

    def run(self):
        try:
            print("⏳ Stabilizing connection (2s)...")
            time.sleep(2)
            
            last_sl_check = 0
            while True:
                now_ts = time.time()

                # EOD Auto-Reset (3:15 PM for NFO, 11:15 PM for MCX)
                ist = pytz.timezone('Asia/Kolkata')
                now = datetime.now(ist).time()
                
                # Check for reset time (15 mins before close)
                close_time = self.state.config['MARKET_CLOSE']
                reset_hour = (close_time.hour if close_time.minute >= 15 else close_time.hour - 1)
                reset_min = (close_time.minute - 15) if close_time.minute >= 15 else (60 + close_time.minute - 15)
                
                if not self.state.config['SIMULATION'] and now >= dt_time(reset_hour, reset_min) and self.state.active_positions:
                    self.executor.square_off_all(self.state, reason="Market Close Reset")
                
                # Evaluation Cycle
                scores = {}
                self.state.last_scan_metrics = []
                for token in self.state.symbols:
                    score = self.evaluator.evaluate_filters(self.state, token)
                    if score != 0: scores[token] = score
                
                # Execute Signals
                self.executor.rank_signals(self.state, scores, self.syncer)

                # SL/TP Monitoring
                if now_ts - last_sl_check >= 60:
                    exit_hits = self.executor.check_sl(self.state, self.syncer)
                    if exit_hits:
                        print(f"🔔 SL/TP Hits: {len(exit_hits)} positions squared off")
                    last_sl_check = now_ts
                
                # Scan Metrics Logging
                from bot.sheets import log_scan_metrics
                if log_scan_metrics and self.state.last_scan_metrics:
                    if now_ts - self.state.last_scan_log_ts >= 60:
                        seg_name = self.state.config.get('segment_name', 'nfo')
                        log_scan_metrics(self.state.last_scan_metrics, segment_name=seg_name)
                        self.state.last_scan_log_ts = now_ts
                        self.syncer.sync_active_positions_to_sheets(self.state)

                time.sleep(self.state.config.get('UPDATE_INTERVAL', 5))
                
        except KeyboardInterrupt:
            print("\n👋 Shutdown complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulation", action="store_true")
    parser.add_argument("--exchange", type=str, help="Exchange to trade (nfo/mcx)")
    args = parser.parse_args()

    # Logic: if --exchange="" then throw error
    if args.exchange is not None and args.exchange.strip() == "":
        print("❌ Error: --exchange cannot be empty. Please pass 'nfo' or 'mcx'.")
        sys.exit(1)

    bot = Orbiter(exchange_override=args.exchange, simulation=args.simulation)
    bot.setup()
    if bot.login():
        bot.run()
