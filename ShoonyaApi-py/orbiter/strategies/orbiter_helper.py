# orbiter/strategies/orbiter_helper.py
"""
🚀 ORBITER Helper - Complete Trading Logic
"""
from utils.utils import safe_ltp, format_score, get_today_orb_times
from datetime import datetime, time as dt_time
import pytz

# Add to TOP:
import sys, os
import importlib.util
import os

# Load sheets.py dynamically from bot/ folder
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("sheets", base_dir+"/bot/sheets.py")
sheets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sheets)
log_buy_signals = sheets.log_buy_signals  # ✅ WORKS EVERYWHERE

class OrbiterHelper:
    def __init__(self, client, symbols, filters, config):
        self.client = client
        self.symbols = symbols
        self.filters = filters
        self.config = config
        
    def evaluate_filters(self, token):
        """Evaluate entry filters"""
        data = self.client.SYMBOLDICT.get(token)
        if not data: 
            print(f"❌ NO DATA for token {token}")
            return 0
        
        print(f"🔍 RAW DATA KEYS: {list(data.keys())}")
        
        # 🔥 FIXED: tk = REAL websocket token, fallback to param
        websocket_token = data.get('tk') or data.get('token') or token
        print(f"🔍 websocket='{websocket_token}' ltp={data.get('lp', 'MISSING')}")
        
        ltp, ltp_display = safe_ltp(data)
        startime, endtime = get_today_orb_times()
        orb_start_ts = int(startime.timestamp())      # 2026-02-06 09:15
        orb_end_ts = int(endtime.timestamp())  
        try:
            candle_data = self.client.api.get_time_price_series(
                exchange='NSE', 
                # token=websocket_token,
                token='2885',
                starttime=orb_start_ts, 
                endtime=orb_end_ts, 
                interval=1
            )
        
            if not candle_data or len(candle_data) < 5:
                print(f"🔴 5EMA {token}: Insufficient data ({len(candle_data)})")
                return 0
            scores = [
                self.filters.orb_filter(data, candle_data, token=websocket_token),  # PASS tk!
                self.filters.price_above_5ema_filter(data, candle_data, token=websocket_token), 
                0
            ]
            
            total = sum(w * s for w, s in zip(self.config['ENTRY_WEIGHTS'], scores))
            return total
        
        except Exception as e:
            print(f"❌ 5EMA ERROR {token}: {e}")
            return 0
  
    def evaluate_all(self):
        """Scan all symbols"""
        scores = {}
        for token in self.symbols:
            # Use FULL token key - NO stripping needed!
            if token not in self.client.SYMBOLDICT:
                continue
                
            score = self.evaluate_filters(token)
            if score > 0:
                scores[token] = score
                
        print(f"📊 Scanned {len(self.symbols)} → {len(scores)} signals")
        if not scores:
            print("🔧 Filters: ['F1:25', 'F2:OFF', 'F3:OFF']")
            print("⏳ Waiting for WebSocket data...")
            
        return scores

    # In your rank_signals() method:
    def rank_signals(self, scores):
        buy_signals = []  # ⭐ ONLY 45pt+ trades
        
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:self.config['TOP_N']]
        
        for token, score in ranked:
            if score >= self.config['TRADE_SCORE']:  # 45pts
                data = self.client.SYMBOLDICT.get(token)
                ltp, symbol = safeltp(data)
                
                buy_signals.append({
                    'token': token,
                    'symbol': symbol,
                    'ltp': ltp,
                    'orb_high': 1074.50,  # From your ORB calc
                    'ema5': 1072.60,      # From your EMA calc
                    'score': score
                })
        
        # ⭐ LOG ONLY BUY TRADES
        if buy_signals:
            log_buy_signals(buy_signals)
        
        return buy_signals  # Return only buy-worthy signals
    
    def is_market_hours(self):
        """🔍 MOVED HERE - Check trading hours IST"""
        now = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        return (self.config['MARKET_OPEN'] <= now <= self.config['MARKET_CLOSE'])

# 🔥 ADD THESE 3 LINES AT BOTTOM:
if __name__ == "__main__":
    pass