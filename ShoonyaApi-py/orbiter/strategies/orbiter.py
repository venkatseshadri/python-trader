#!/usr/bin/env python3
"""
🚀 ORBITER - NIFTY F&O ORB Trading Bot (FIXED VERSION)
TOP 7 Execution | Modular Filters | Shoonya API
"""

import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.client import BrokerClient
from filters import *
from config import SYMBOLS_UNIVERSE, TOP_N, TRADE_SCORE
from operator import itemgetter
from utils.utils import safe_ltp, format_position
from datetime import datetime, time as time_class
import pytz

def dt_time(hour, minute):
    """Market time helper - FIXED"""
    return time_class(hour, minute)

class OrbiterStrategy:
    def __init__(self, client):
        self.client = client  # Pass client from main
        self.load_config()
        self.load_components()
        
    def load_config(self):
        """Load TOP_N, TRADE_SCORE from config.py"""
        self.TRADE_SCORE = TRADE_SCORE
        self.TOP_N = TOP_N
        self.ENTRY_WEIGHTS = [25.0, 20.0, 18.0]  # F1,F2,F3 weights
        self.SL_WEIGHTS = [1.0] * 10
        
        # Trading hours IST
        ist = pytz.timezone('Asia/Kolkata')
        self.MARKET_OPEN = dt_time(9, 15)
        self.MARKET_CLOSE = dt_time(15, 30)
        
        print("🚀 NIFTY F&O Universe loaded")
        print(f"📈 TOP {self.TOP_N} execution | Min score: {self.TRADE_SCORE}pts")
        
    def load_components(self):
        """Load universe and filters - FIXED"""
        print("✅ Modular filters + config loaded!")
        
        # Use existing config.py SYMBOLS_UNIVERSE
        self.symbols = SYMBOLS_UNIVERSE
        print(f"📊 Universe: {len(self.symbols)} NIFTY F&O stocks")
        
        # Direct filter functions (no FilterManager class needed)
        self.filters = {
            'f1_orb': orb_filter,
            'f2_5ema': price_above_5ema_filter,
            'f3_9ema': ema5_above_9ema_filter
        }
        print(f"🎯 Filters: F1(25)+F2(20)+F3(18) | TOP {self.TOP_N}")
        
    def evaluate_filters(self, token):
        """Evaluate entry filters for token - FIXED"""
        data = self.client.SYMBOLDICT.get(token)
        if not data:
            return 0
            
        ltp, ltp_display = safe_ltp(data)
    
        # Apply actual filter functions
        scores = [
            self.filters['f1_orb'](data),           # F1 ORB
            self.filters['f2_5ema'](data),         # F2 5EMA
            self.filters['f3_9ema'](data)          # F3 9EMA
        ]
        
        total = sum(w * s for w, s in zip(self.ENTRY_WEIGHTS, scores))
        return total
        
    def evaluate_all(self):
        """Evaluate all symbols - TOKEN FORMAT FIX"""
        scores = {}
        skipped = 0

        for full_token in self.symbols:

            if full_token in self.client.SYMBOLDICT:
                score = self.evaluate_filters(full_token)
                if score > 0:
                    scores[full_token] = score
            else:
                skipped += 1
                
        print(f"📊 Scanned {len(self.symbols)} → {len(scores)} signals ({skipped} skipped)")
        return scores

    def rank_signals(self, scores):
        """Rank top signals - FIXED format_score"""
        if not scores:
            return []
            
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:self.TOP_N]
        print("\n🏆 RANKING (Top {}):".format(self.TOP_N))
        for i, (token, score) in enumerate(ranked, 1):
            data = self.client.SYMBOLDICT.get(token)
            name = self.client.SYMBOLDICT.get(token)['ts'].replace('-EQ', '')
            ltp, ltp_display = safe_ltp(data) if data else (0, "N/A")
            status = "🟢 ENTRY" if score >= self.TRADE_SCORE else "⚪ MONITOR"
            print(f"  {i}. {name} {ltp_display} = {score:.0f}pts {status}")
            
        return [(token, score) for token, score in ranked if score >= self.TRADE_SCORE]
        
    def is_market_hours(self):
        """Check market hours 9:15-15:30 IST"""
        now = datetime.now()
        now_ist = now.astimezone(pytz.timezone('Asia/Kolkata'))
        current_time = now_ist.time()
        return self.MARKET_OPEN <= current_time <= self.MARKET_CLOSE
        
    def run(self):
        """Main trading loop - NEEDS WEBSOCKET START"""
        # CRITICAL: Start WebSocket feed FIRST
        print("🚀 Starting WebSocket feed...")
        self.client.start_live_feed(self.symbols)
        
        try:
            while True:
                # if not self.is_market_hours():
                #     print("😴 Outside market hours (9:15-15:30 IST)")
                #     time.sleep(60)
                #     continue
                    
                scores = self.evaluate_all()
                entry_signals = self.rank_signals(scores)
                
                if entry_signals:
                    print(f"\n🚀 {len(entry_signals)} ENTRY SIGNALS!")
                    for token, score in entry_signals:
                        name = self.client.SYMBOLDICT.get(token)['ts'].replace('-EQ', '')
                        print(f"   🎯 BUY {name} ({score:.0f}pts)")
                        # TODO: self.client.place_order(...)
                else:
                    print("⏳ No signals")
                    
                time.sleep(5)  # Scan every 5 seconds
                
        except KeyboardInterrupt:
            print("\n👋 Shutdown complete")
        except Exception as e:
            print(f"💥 ERROR: {e}")
            raise

if __name__ == "__main__":
    client = BrokerClient()
    if client.login():
        print("✅ Broker connected!")
        orbiter = OrbiterStrategy(client)  # Pass client
        orbiter.run()
    else:
        print("❌ Login failed")
