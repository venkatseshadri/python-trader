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
log_square_off = getattr(sheets, 'log_square_off', None)

# SL filters - dynamic load from orbiter/filters/sl
sl_f1 = None
try:
    sl_path = os.path.join(base_dir, 'filters', 'sl', 'f1_price_drop_10.py')
    if os.path.exists(sl_path):
        sl_spec = importlib.util.spec_from_file_location('sl_f1', sl_path)
        sl_f1 = importlib.util.module_from_spec(sl_spec)
        sl_spec.loader.exec_module(sl_f1)
except Exception:
    sl_f1 = None

class OrbiterHelper:
    def __init__(self, client, symbols, filters, config):
        self.client = client
        self.symbols = symbols
        self.filters = filters
        self.config = config
        # ⭐ NEW: Track active buy positions: token -> info
        # info = {'entry_price': float, 'entry_time': datetime, 'symbol': str, 'company_name': str}
        self.active_positions = {}  # {'NSE|3045': {...}}
        
    def evaluate_filters(self, token):
        """Evaluate entry filters - Store returnvalues + return numeric total"""
        data = self.client.SYMBOLDICT.get(token)
        if not data: 
            print(f"❌ NO DATA for token {token}")
            return 0
        
        print(f"🔍 RAW DATA KEYS: {list(data.keys())}")
        websocket_token = data.get('tk') or data.get('token') or token
        print(f"🔍 websocket='{websocket_token}' ltp={data.get('lp', 'MISSING')}")
        
        #ltp, ltp_display, symbol  = safe_ltp(data)
        startime, endtime = get_today_orb_times()
        orb_start_ts = int(startime.timestamp())
        orb_end_ts = int(endtime.timestamp())
        
        try:
            candle_data = self.client.api.get_time_price_series(
                exchange='NSE', 
                token=websocket_token,
                starttime=orb_start_ts, 
                endtime=orb_end_ts, 
                interval=1
            )
        
            if not candle_data or len(candle_data) < 5:
                print(f"🔴 5EMA {token}: Insufficient data ({len(candle_data)})")
                return 0
            
            # ⭐ Get FULL returnvalues from filters
            orb_result = self.filters.orb_filter(data, candle_data, token=websocket_token)
            ema_result = self.filters.price_above_5ema_filter(data, candle_data, token=websocket_token)
            
            # ⭐ Extract JUST scores for evaluation
            scores = [
                orb_result['score'],    # 25 or 0
                ema_result['score'],    # 20 or 0  
                0                       # F3 OFF
            ]
            
            total = sum(w * s for w, s in zip(self.config['ENTRY_WEIGHTS'], scores))
            
            # ⭐ STORE returnvalues for rank_signals() to use later
            data['_filter_results'] = {
                'orb': orb_result,      # {'score':25, 'orb_high':1074.50, 'orb_low':1067.20}
                'ema': ema_result,      # {'score':20, 'ema5':1072.15}
                'total': total          # 45
            }
            
            print(f"📊 {token}: ORB={orb_result['score']} EMA={ema_result['score']} TOTAL={total}")
            return total  # ⭐ ONLY numeric total for ranking
            
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
        buy_signals = []
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:self.config['TOP_N']]
        
        print(f"🔍 DEBUG: active_positions={self.active_positions}")  # ⭐ SEE STATE
        
        for token, score in ranked:
            print(f"🔍 CHECKING {token}: {score}pts")  # ⭐ DEBUG
            
            # ⭐ SKIP if already in position (BEFORE 45pt check)
            if token in self.active_positions:
                print(f"⏭️ SKIP {token} - Position active")
                continue

            # ⭐ 45pt CONFIRMED → NEW POSITION
            if score >= self.config['TRADE_SCORE']:  # 45pts
                print(f"🟢 NEW BUY: {token} {score}pts")  # ⭐ CONFIRMED
                
                data = self.client.SYMBOLDICT.get(token)
                # WITH:  
                filter_results = data.get('_filter_results', {
                    'orb': {'orb_high': data.get('high', 0), 'orb_low': data.get('low', 0)},
                    'ema': {'ema5': data.get('ltp', 0)}
                })
                ltp, ltp_display, symbol = safe_ltp(data)  # ✅ 3 values

                buy_signals.append({
                    'token': token,
                    'symbol': symbol,           # RELIANCE
                    'company_name': data.get('company_name', symbol),  # ✅ Use company name from websocket data
                    'ltp': ltp,
                    'ltp_display': ltp_display, # ₹1446.40 (bonus)
                    'orb_high': filter_results['orb']['orb_high'],
                    'orb_low': filter_results['orb']['orb_low'],
                    'ema5': filter_results['ema']['ema5'],
                    'score': score
                })
                
                # ⭐ ADD TO POSITIONS IMMEDIATELY (inside 45pt block)
                self.active_positions[token] = {
                    'entry_price': ltp,
                    'entry_time': datetime.now(pytz.timezone('Asia/Kolkata')),
                    'symbol': symbol,
                    'company_name': data.get('company_name', symbol)
                }
                print(f"✅ POSITION ADDED: {token} @ {ltp}")
        
        # ⭐ LOG ONLY NEW 45pt SIGNALS
        if buy_signals:
            log_buy_signals(buy_signals)
            print(f"✅ {len(buy_signals)} NEW buys → Google Sheets")
        
        return buy_signals

    def check_sl(self):
        """Periodically called to evaluate SL filters for active positions."""
        if not self.active_positions:
            return []

        to_square = []
        for token, info in list(self.active_positions.items()):
            # get latest LTP
            data = self.client.SYMBOLDICT.get(token) or {}
            ltp = None
            try:
                ltp = float(data.get('ltp')) if data.get('ltp') is not None else self.client.get_ltp(token)
            except Exception:
                ltp = self.client.get_ltp(token)

            if ltp is None:
                continue

            # run SL filters (start with f1_price_drop_10)
            if not sl_f1:
                continue
            res = sl_f1.check_sl(info, float(ltp))
            if res.get('hit'):
                pct = res.get('pct', 0.0)
                reason = res.get('reason', 'SL HIT')
                so = {
                    'token': token,
                    'symbol': info.get('symbol'),
                    'company_name': info.get('company_name'),
                    'entry_price': info.get('entry_price'),
                    'exit_price': float(ltp),
                    'pct_change': pct,
                    'reason': reason
                }
                to_square.append(so)
                # remove position
                try:
                    del self.active_positions[token]
                except KeyError:
                    pass

        # log square offs
        if to_square and log_square_off:
            log_square_off(to_square)
        return to_square

    
    def is_market_hours(self):
        """🔍 MOVED HERE - Check trading hours IST"""
        now = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        return (self.config['MARKET_OPEN'] <= now <= self.config['MARKET_CLOSE'])

# 🔥 ADD THESE 3 LINES AT BOTTOM:
if __name__ == "__main__":
    pass