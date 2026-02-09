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
from config import SYMBOLS_UNIVERSE, TOP_N, TRADE_SCORE
from orbiter_helper import OrbiterHelper
import config

class Orbiter:
    def __init__(self):        
        self.config = {
            'TRADE_SCORE': 25,
            'TOP_N': 6,
            'ENTRY_WEIGHTS': [1.0, 1.0, 0.0],
            'MARKET_OPEN': dt_time(9, 15),
            'MARKET_CLOSE': dt_time(15, 30)
        }
        
        self.client = None
        self.helper = None
        
    def setup(self):
        """Load all components"""
        print("✅ Modular filters + config loaded!")
        
        symbols = config.SYMBOLS_UNIVERSE
        self.client = BrokerClient("../cred.yml")
        self.helper = OrbiterHelper(self.client, symbols, filters, self.config)

        print(f"📊 Universe: {len(symbols)} NIFTY F&O stocks")
        print(f"🎯 Entry: TOP {self.config['TOP_N']} ≥ {self.config['TRADE_SCORE']}pts")
        
    def login(self):
        """Shoonya login - NO NEW CLIENT!"""
        symbols = config.SYMBOLS_UNIVERSE
        # print("🚀 BrokerClient initialized:", self.client.cred['user'])  # FA333160
        # print("🔐 Authenticating...")
        self.client.login()  # Uses EXISTING client
        self.client.start_live_feed(symbols)

    def is_eod_reset_time(self):
        """⭐ EOD RESET: Clear positions at 3:25PM"""
        now = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        eod_reset = time(15, 25)  # 3:25PM
        return now >= eod_reset

    def run(self):
        """Main orchestrator"""
        try:
            last_sl_check = 0
            while True:
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
                now = time.time()
                if now - last_sl_check >= 60:
                    sl_hits = self.helper.check_sl()
                    if sl_hits:
                        print(f"🔔 SL Hits: {len(sl_hits)} positions squared off")
                    last_sl_check = now
                
                if entry_signals:
                    print(f"\n🚀 {len(entry_signals)} ENTRY SIGNALS!")
                    
                time.sleep(5)
                
        except KeyboardInterrupt:
            print("\n👋 Shutdown complete")

def main():
    orbiter = Orbiter()
    orbiter.setup()
    orbiter.login()
    orbiter.run()

if __name__ == "__main__":
    main()