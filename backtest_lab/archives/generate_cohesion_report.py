import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader

# LOT SIZES
LOT_SIZES = {"RELIANCE": 250, "TCS": 175, "LT": 175, "SBIN": 750, "HDFCBANK": 550, "INFY": 400, "ICICIBANK": 700, "AXISBANK": 625, "BHARTIARTL": 475, "KOTAKBANK": 400}

def resample_data(df, interval_min):
    df = df.set_index('date')
    resampled = df.resample(f'{interval_min}min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    return resampled.reset_index()

class CohesionMTFEngine:
    def __init__(self, top_n=5, threshold=0.35):
        self.top_n = top_n
        self.threshold = threshold
        self.active_positions = {} 
        self.all_trades = []
        self.weights = [1.0, 0.5, 1.2, 0.6, 1.0, 1.2, 0.8, 1.5]

    def run_simulation(self, stock_data_dict):
        stock_names = list(stock_data_dict.keys())
        # We find the min/max index based on the first stock
        max_len = len(stock_data_dict[stock_names[0]]['1m'])
        
        # 1. Pre-calc ORB
        orb_levels = {}
        for name in stock_names:
            df_1m = stock_data_dict[name]['1m']
            mask = (df_1m['date'].dt.time >= dt_time(9, 15)) & (df_1m['date'].dt.time <= dt_time(10, 0))
            if not df_1m.empty and mask.any():
                orb_levels[name] = {'h': df_1m.loc[mask, 'high'].max(), 'l': df_1m.loc[mask, 'low'].min()}
            else: orb_levels[name] = None

        for i in range(45, max_len):
            # i is the index for 1-minute data
            to_close = []
            for name, pos in self.active_positions.items():
                df_1m = stock_data_dict[name]['1m']
                if i >= len(df_1m): continue
                row = df_1m.iloc[i]
                ltp, ts = row['close'], row['date']
                
                # Exit on 5m EMA Reversal (Faster than 15m, slower than 1m)
                e5_5m, e9_5m = row['ema5_5m'], row['ema9_5m']
                exit_hit = (pos['type'] == 'LONG' and e5_5m < e9_5m) or (pos['type'] == 'SHORT' and e5_5m > e9_5m)
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    pnl_pts = (ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)
                    self.all_trades.append({
                        'Time': pos['entry_time'], 'Stock': name, 'Action': f"ENTRY ({pos['type']})",
                        'Price': pos['in'], 'PnL_Rs': '-', 'Reason': pos['entry_reason']
                    })
                    self.all_trades.append({
                        'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_pts * LOT_SIZES.get(name, 50), 2), 
                        'Reason': f"5m_EMA_EXIT | Score: {pos['entry_score']:.2f}"
                    })
                    to_close.append(name)
            
            for name in to_close: del self.active_positions[name]

            if len(self.active_positions) >= self.top_n: continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df_1m = stock_data_dict[name]['1m']
                if i < 1 or i >= len(df_1m): continue
                
                score, breakdown, is_cohesive = self._calc_cohesion_score(name, orb_levels[name], df_1m, i)
                
                if is_cohesive and abs(score) >= self.threshold:
                    candidates.append({'name': name, 'score': score, 'breakdown': breakdown, 'ltp': df_1m['close'].iloc[i], 'time': df_1m['date'].iloc[i]})

            ranked = sorted(candidates, key=lambda x: abs(x['score']), reverse=True)
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {
                    'in': c['ltp'], 'type': 'LONG' if c['score'] > 0 else 'SHORT', 
                    'entry_time': c['time'], 'entry_reason': c['breakdown'], 'entry_score': c['score']
                }

    def _calc_cohesion_score(self, name, orb, df, i):
        if not orb: return 0, "", False
        row = df.iloc[i]
        prev = df.iloc[i-1]
        ltp = row['close']
        
        # 1. CORE FILTERS
        f1 = 0.25 if ltp > orb['h'] else (-0.25 if ltp < orb['l'] else 0)
        f2 = (ltp - row['ema5_1m']) / ltp * 10
        # F3 uses 5m EMA for stability
        f3 = 0.20 if row['ema5_5m'] > row['ema9_5m'] else -0.20
        # F8 uses 15m ADX for major trend
        f8 = 0.25 if row['adx_15m'] > 25 and row['adx_15m'] > prev['adx_15m'] else 0
        
        raw_scores = [f1, f2, f3, 0, 0, 0, 0, f8]
        total = sum(r * w for r, w in zip(raw_scores, self.weights))
        
        # 2. COHESION CHECK (No Mixed Signs for Core Filters F1, F3, F8)
        # For LONG: F1, F3, F8 must all be >= 0
        # For SHORT: F1, F3, F8 must all be <= 0
        is_long_cohesive = (f1 >= 0 and f3 >= 0 and f8 >= 0)
        is_short_cohesive = (f1 <= 0 and f3 <= 0 and f8 <= 0)
        is_cohesive = is_long_cohesive or is_short_cohesive
        
        details = f"Cohesive:{is_cohesive} | Score:{total:.2f} (F1:{f1:.2f}, F2:{f2:.2f}, F3_5m:{f3:.2f}, F8_15m:{f8:.2f})"
        return total, details, is_cohesive

def run_cohesion_mtf_simulation(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    target_date = pd.to_datetime(target_date_str).date()
    
    stock_data = {}
    for s in top_stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df_1m = loader.load_data(days=15)
        
        # Multi-Timeframe Prep
        df_5m = resample_data(df_1m, 5)
        df_15m = resample_data(df_1m, 15)
        
        # Calculate Indicators on respective timeframes
        df_5m['ema5_5m'] = talib.EMA(df_5m['close'].values.astype(float), 5)
        df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 9)
        df_15m['adx_15m'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
        
        # Map back to 1m
        df_1m['ema5_1m'] = talib.EMA(df_1m['close'].values.astype(float), 5)
        df_1m = df_1m.merge(df_5m[['date', 'ema5_5m', 'ema9_5m']], on='date', how='left').ffill()
        df_1m = df_1m.merge(df_15m[['date', 'adx_15m']], on='date', how='left').ffill()
        
        stock_data[s] = {'1m': df_1m[df_1m['date'].dt.date == target_date].reset_index(drop=True)}

    engine = CohesionMTFEngine(top_n=5, threshold=0.35)
    engine.run_simulation(stock_data)
    
    df_res = pd.DataFrame(engine.all_trades)
    
    # Save Report
    html_file = f"python-trader/backtest_lab/reports/cohesion_mtf_report_{target_date_str}.html"
    df_res.to_html(html_file)
    print(f"✅ Cohesion MTF Report generated: {html_file}")

if __name__ == "__main__":
    run_cohesion_mtf_simulation("2026-01-21")
