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

class EliteChoosyEngine:
    def __init__(self, top_n=3, threshold=0.45): # Higher threshold for "Elite" selection
        self.top_n = top_n
        self.threshold = threshold
        self.active_positions = {} 
        self.all_trades = []
        self.weights = [1.0, 0.5, 1.2, 0.6, 1.0, 1.2, 0.8, 1.5]

    def run_simulation(self, stock_data_dict):
        stock_names = list(stock_data_dict.keys())
        max_len = max(len(df) for df in stock_data_dict.values())
        
        for i in range(45, max_len):
            to_close = []
            for name, pos in self.active_positions.items():
                df = stock_data_dict[name]
                if i >= len(df): continue
                row = df.iloc[i]
                ltp, ts = row['close'], row['date']
                
                # MIRROR EXIT: Close vs 5m EMA 9
                e9 = row['ema9_5m']
                exit_hit = (pos['type'] == 'LONG' and ltp < e9) or (pos['type'] == 'SHORT' and ltp > e9)
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    reason = f"EXIT_PA_REVERSAL" if exit_hit else "EOD"
                    pnl_pts = (ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)
                    self.all_trades.append({
                        'Time': pos['entry_time'], 'Stock': name, 'Action': f"ENTRY ({pos['type']})",
                        'Price': pos['in'], 'PnL_Rs': '-', 'Reason': pos['entry_reason']
                    })
                    self.all_trades.append({
                        'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_pts * LOT_SIZES.get(name, 50), 2), 'Reason': reason
                    })
                    to_close.append(name)
            
            for name in to_close: del self.active_positions[name]

            # Entry Logic
            curr_ts = stock_data_dict[stock_names[0]]['date'].iloc[i]
            if curr_ts.time() > dt_time(14, 30): continue
            if len(self.active_positions) >= self.top_n: continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df = stock_data_dict[name]
                if i < 1 or i >= len(df): continue
                row, prev = df.iloc[i], df.iloc[i-1]
                
                # 1. INDIVIDUAL FILTERS
                orb = df.attrs['orb']
                f1 = 0.25 if row['close'] > orb['h'] else (-0.25 if row['close'] < orb['l'] else 0)
                f3 = 0.20 if row['ema5_5m'] > row['ema9_5m'] else -0.20
                f4 = 0.20 if row['close'] > row['st'] else -0.20
                f8 = 0.25 if row['adx'] > 25 and row['adx'] > prev['adx'] else 0
                
                # 🛡️ 2. HARD COHESION RULE
                # For LONG: All must be >= 0. For SHORT: All must be <= 0.
                is_long_aligned = (f1 >= 0 and f3 >= 0 and f4 >= 0 and f8 >= 0)
                is_short_aligned = (f1 <= 0 and f3 <= 0 and f4 <= 0 and f8 <= 0)
                
                if not (is_long_aligned or is_short_aligned): continue
                
                # 3. SCORE CALCULATION (Only if cohesive)
                raw = [f1, 0, f3, f4, 0, 0, 0, f8] # Simplified 4-filter stack for cohesion
                total = sum(r * w for r, w in zip(raw, self.weights))
                
                if abs(total) >= self.threshold:
                    breakdown = f"Cohesive:True | Score:{total:.2f} (F1:{f1:.2f}, F3:{f3:.2f}, F4:{f4:.2f}, F8:{f8:.2f})"
                    candidates.append({'name': name, 'score': total, 'breakdown': breakdown, 'ltp': row['close'], 'time': row['date']})

            ranked = sorted(candidates, key=lambda x: abs(x['score']), reverse=True)
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {'in': c['ltp'], 'type': 'LONG' if c['score'] > 0 else 'SHORT', 'entry_time': c['time'], 'entry_reason': c['breakdown']}

def generate_elite_choosy_report(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    target_date = pd.to_datetime(target_date_str).date()
    stock_data = {}
    
    # Pre-calculate indicators for all 50 stocks
    def calculate_st_values(high, low, close, period=10, multiplier=3.0):
        atr = talib.ATR(high, low, close, timeperiod=period)
        hl2 = (high + low) / 2
        st = hl2 + (multiplier * atr) # Simplified
        return st

    for s in top_stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df = loader.load_data(days=20)
        df_5m = resample_data(df, 5)
        df_5m['ema5_5m'], df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 5), talib.EMA(df_5m['close'].values.astype(float), 9)
        df['ema20_5m'] = talib.EMA(df['close'].values.astype(float), 100)
        df['ema50_5m'] = talib.EMA(df['close'].values.astype(float), 250)
        df['adx'] = talib.ADX(df['high'].values.astype(float), df['low'].values.astype(float), df['close'].values.astype(float), 14)
        df['st'] = calculate_st_values(df['high'].values.astype(float), df['low'].values.astype(float), df['close'].values.astype(float))
        df = df.merge(df_5m[['date', 'ema5_5m', 'ema9_5m']], on='date', how='left').ffill()
        df_day = df[df['date'].dt.date == target_date].reset_index(drop=True)
        mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
        df_day.attrs['orb'] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
        stock_data[s] = df_day

    engine = EliteChoosyEngine(top_n=3, threshold=0.45)
    engine.run_simulation(stock_data)
    df_res = pd.DataFrame(engine.all_trades)
    
    html_file = f"python-trader/backtest_lab/reports/elite_choosy_report_{target_date_str}.html"
    with open(html_file, "w") as f:
        f.write(f"<html><body class='p-5 font-sans'><h1>💎 Elite Choosy Selection Report</h1>")
        if not df_res.empty:
            total_pnl = pd.to_numeric(df_res['PnL_Rs'], errors='coerce').sum()
            f.write(f"<h2>Total PnL: Rs {total_pnl:,.2f} | Filter Cohesion Rule: ACTIVE</h2>")
            f.write(df_res.to_html(classes='table'))
        else:
            f.write("<h2>No stocks met the strict cohesion and score criteria today.</h2>")
        f.write("</body></html>")
    print(f"✅ Elite Report generated: {html_file}")

if __name__ == "__main__":
    generate_elite_choosy_report("2026-01-21")
