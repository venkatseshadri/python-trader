#!/usr/bin/env python3
"""
🚀 ORBITER v2.0 - Ultra Clean Main Runner
"""

import time
import sys
import os

import pytz
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir) 
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, time as dt_time
from core.client import BrokerClient
import filters
from orbiter_helper import OrbiterHelper
import config

class Orbiter:
    def __init__(self):        
        self.config = {
            'TRADE_SCORE': config.TRADE_SCORE,
            'TOP_N': config.TOP_N,
            'ENTRY_WEIGHTS': config.ENTRY_WEIGHTS,
            'MARKET_OPEN': config.MARKET_OPEN,
            'MARKET_CLOSE': config.MARKET_CLOSE,
            'OPTION_EXECUTE': config.OPTION_EXECUTE,
            'OPTION_PRODUCT_TYPE': config.OPTION_PRODUCT_TYPE,
            'OPTION_PRICE_TYPE': config.OPTION_PRICE_TYPE,
            'OPTION_EXPIRY': config.OPTION_EXPIRY,
            'OPTION_INSTRUMENT': config.OPTION_INSTRUMENT,
            'HEDGE_STEPS': config.HEDGE_STEPS
        }
        
        self.client = None
        self.helper = None
        
    def setup(self):
        """Load all components"""
        print("✅ Modular filters + config loaded!")
        
        symbols = config.SYMBOLS_UNIVERSE
        self.client = BrokerClient("../ShoonyaApi-py/cred.yml")
        self.helper = OrbiterHelper(self.client, symbols, filters, self.config)

        print(f"📊 Universe: {len(symbols)} NIFTY F&O stocks")
        print(f"🎯 Entry: TOP {self.config['TOP_N']} ≥ {self.config['TRADE_SCORE']}pts")
        
    def login(self, factor2_override: str | None = None):
        """Shoonya login - NO NEW CLIENT!"""
        symbols = self.helper.symbols
        # print("🚀 BrokerClient initialized:", self.client.cred['user'])  # FA333160
        # print("🔐 Authenticating...")
        ok = self.client.login(factor2_override=factor2_override)  # Uses EXISTING client
        if not ok:
            print("🛑 Aborting: login failed, websocket not started")
            return False
        self.client.start_live_feed(symbols)
        return True

    def is_eod_reset_time(self):
        """⭐ EOD RESET: Clear positions at 3:25PM"""
        now = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        eod_reset = dt_time(15, 25)  # 3:25PM
        return now >= eod_reset

    def run(self):
        """Main orchestrator"""
        try:
            last_sl_check = 0
            while True:
                now_ts = time.time()

                # if not self.helper.is_market_hours():  # ← MOVED!
                #     print("😴 Outside market hours")
                #     time.sleep(60)
                #     continue

                # # ⭐ EOD AUTO-RESET
                # if self.is_eod_reset_time():
                #     self.helper.active_positions.clear()
                #     print("🔄 EOD 3:25PM: All positions RESET")
                
                scores = self.helper.evaluate_all()
                entry_signals = self.helper.rank_signals(scores)

                # Periodically check SLs every 60 seconds
                if now_ts - last_sl_check >= 60:
                    sl_hits = self.helper.check_sl()
                    if sl_hits:
                        print(f"🔔 SL Hits: {len(sl_hits)} positions squared off")
                    last_sl_check = now_ts
                
                if entry_signals:
                    print(f"\n🚀 {len(entry_signals)} ENTRY SIGNALS!")
                    
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n👋 Shutdown complete")

def main():
    orbiter = Orbiter()
    orbiter.setup()
    if not orbiter.login():
        return
    orbiter.run()

if __name__ == "__main__":
    main()