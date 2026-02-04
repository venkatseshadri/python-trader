#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.client import BrokerClient
from filters import *
from config import SYMBOLS_UNIVERSE, TOP_N, TRADE_SCORE
import time
from operator import itemgetter

print("✅ Modular filters + config loaded!")
print(f"📊 Universe: {len(SYMBOLS_UNIVERSE)} NIFTY F&O stocks")
print(f"🎯 Execute TOP {TOP_N} ≥ {TRADE_SCORE}pts")

class OrbiterStrategy:
    FILTERS = [orb_filter, price_above_5ema_filter, ema5_above_9ema_filter]
    WEIGHTS = [25, 20, 18]
    
    def __init__(self, client):
        self.client = client
        self.ema_histories = {}
        self.symbols = SYMBOLS_UNIVERSE
        self.trade_count = 0
    
    def safe_ltp(self, token):
        """🔥 SAFE LTP conversion - handles string/float issues"""
        try:
            ltp_raw = self.client.SYMBOLDICT[token].get('lp', '0')
            ltp = float(ltp_raw) if ltp_raw else 0.0
            return ltp, f"₹{ltp:.2f}"
        except (ValueError, TypeError):
            return 0.0, "₹0.00"
    
    def evaluate_filters(self, token):
        if token not in self.client.SYMBOLDICT:
            return 0
        data = self.client.SYMBOLDICT[token]
        scores = []
        for f, w in zip(self.FILTERS, self.WEIGHTS):
            score = f(data, w, self.ema_histories)
            scores.append(score)
        total = sum(scores)
        tsym = data.get('ts', token)
        print(f"📊 {tsym}: {scores} = {total}pts")
        return total
    
    def evaluate_all(self):
        """Evaluate ALL stocks"""
        scores = {}
        for token in self.symbols:
            if token in self.client.SYMBOLDICT:
                scores[token] = self.evaluate_filters(token)
        return scores
    
    def get_top_n_trades(self, scores):
        """SORT → TOP 7 with SAFE LTP display"""
        if not scores:
            print("❌ No stock data")
            return []
        
        sorted_scores = sorted(scores.items(), key=itemgetter(1), reverse=True)
        valid_scores = {k: v for k, v in sorted_scores if k in self.client.SYMBOLDICT}
        
        if not valid_scores:
            print("❌ No valid stocks")
            return []
        
        top_n = sorted(valid_scores.items(), key=itemgetter(1), reverse=True)[:TOP_N]
        
        print("\n🏆 RANKING (Top {}):".format(TOP_N))
        for i, (token, score) in enumerate(top_n, 1):
            tsym = self.client.SYMBOLDICT[token].get('ts', token)
            ltp, ltp_display = self.safe_ltp(token)
            status = "🟢 TRADE!" if score >= TRADE_SCORE else "⚪ MONITOR"
            print(f"  {i}. {tsym} {ltp_display} = {score}pts {status}")
        
        return top_n
    
    def run(self):
        self.client.start_live_feed(self.symbols)
        print(f"\n🚀 ORBITER LIVE - {len(self.symbols)} STOCKS → EXECUTE TOP {TOP_N}!")
        print("F1: ORB(25) | F2: LTP>5EMA(20) | F3: 5EMA>9EMA(18)")
        print("🔔 SIMULATION MODE - NO REAL ORDERS PLACED")
        print("-" * 80)
        
        while True:
            try:
                scores = self.evaluate_all()
                
                if not scores:
                    print("⏳ Waiting for WebSocket data...\n")
                    time.sleep(5)
                    continue
                
                top_trades = self.get_top_n_trades(scores)
                
                if top_trades:
                    # 🔥 EXECUTE ALL TOP 7 WINNERS ≥ TRADE_SCORE!
                    trade_signals = [trade for trade in top_trades if trade[1] >= TRADE_SCORE]
                    
                    if trade_signals:
                        self.trade_count += len(trade_signals)
                        print(f"\n🚀 SESSION: {self.trade_count} signals | EXECUTING {len(trade_signals)}/{TOP_N} TRADES (SIMULATION):")
                        for i, (token, score) in enumerate(trade_signals, 1):
                            tsym = self.client.SYMBOLDICT[token]['ts']
                            ltp, ltp_display = self.safe_ltp(token)
                            sl_price = ltp * 0.98
                            print(f"  {i}. 🟢 BUY {tsym} @ {ltp_display} ({score}pts)")
                            print(f"     📏 Lot: 50 | MIS | NSE | SL: ₹{sl_price:.2f}")
                    else:
                        print(f"\n⏳ NO TRADES (Need {TRADE_SCORE}+pts)")
                else:
                    print("\n❌ No stocks passed filters\n")
                
                print("-" * 80)
                time.sleep(5)
                
            except KeyboardInterrupt:
                print(f"\n\n🛑 ORBITER STOPPED | Total signals: {self.trade_count}")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(5)

if __name__ == "__main__":
    client = BrokerClient()
    if client.login():
        orbiter = OrbiterStrategy(client)
        orbiter.run()
    else:
        print("❌ Login failed")
