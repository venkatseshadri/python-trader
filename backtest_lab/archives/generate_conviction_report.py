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

class ConvictionEngine:
    def __init__(self, top_n=3, threshold=0.45):
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
                lot = LOT_SIZES.get(name, 50)
                
                # PnL Tracking
                pnl_pts = (ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)
                pnl_rs = pnl_pts * lot
                pos['max_pnl_rs'] = max(pos.get('max_pnl_rs', 0), pnl_rs)
                
                exit_hit = False
                reason = ""
                
                # 1. 🛡️ HIGH-VALUE GUARD (Rs 1000 / 30%)
                if pos['max_pnl_rs'] >= 1000:
                    if pnl_rs <= (pos['max_pnl_rs'] * 0.70):
                        exit_hit, reason = True, f"CONVICTION_GUARD (Max:{pos['max_pnl_rs']:.0f})"
                
                # 2. 🛡️ STRUCTURAL 15m EXIT (Breathing Room)
                if not exit_hit:
                    if (pos['type'] == 'LONG' and row['ema5_15m'] < row['ema9_15m']) or (pos['type'] == 'SHORT' and row['ema5_15m'] > row['ema9_15m']):
                        exit_hit, reason = True, "15m_STRUCTURAL_EXIT"
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    if not exit_hit: reason = "EOD"
                    self.all_trades.append({
                        'Time': pos['entry_time'], 'Stock': name, 'Action': f"ENTRY ({pos['type']})",
                        'Price': pos['in'], 'PnL_Rs': '-', 'Reason': pos['entry_reason']
                    })
                    self.all_trades.append({
                        'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_rs, 2), 'Reason': reason,
                        'Duration': round((ts - pos['entry_time']).total_seconds() / 60, 1)
                    })
                    to_close.append(name)
            
            for name in to_close: del self.active_positions[name]

            # Entry
            if i >= max_len or stock_data_dict[stock_names[0]]['date'].iloc[i].time() > dt_time(14, 30): continue
            if len(self.active_positions) >= self.top_n: continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df = stock_data_dict[name]
                if i < 1 or i >= len(df): continue
                row, prev = df.iloc[i], df.iloc[i-1]
                
                orb = df.attrs['orb']
                f1 = 0.25 if row['close'] > orb['h'] else (-0.25 if row['close'] < orb['l'] else 0)
                f3 = 0.20 if row['ema5_5m'] > row['ema9_5m'] else -0.20
                f4 = 0.20 if row['close'] > row['st'] else -0.20
                f8 = 0.25 if row['adx'] > 25 and row['adx'] > prev['adx'] else 0
                
                # COHESION
                is_long = (f1 >= 0 and f3 >= 0 and f4 >= 0 and f8 >= 0)
                is_short = (f1 <= 0 and f3 <= 0 and f4 <= 0 and f8 <= 0)
                if not (is_long or is_short): continue
                
                total = (f1*1.0) + (f3*1.5) + (f4*1.0) + (f8*1.5)
                if abs(total) >= self.threshold:
                    candidates.append({'name': name, 'score': total, 'reason': f"Cohesive Score:{total:.2f}", 'ltp': row['close'], 'time': row['date']})

            ranked = sorted(candidates, key=lambda x: abs(x['score']), reverse=True)
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {'in': c['ltp'], 'type': 'LONG' if c['score'] > 0 else 'SHORT', 'entry_time': c['time'], 'entry_reason': c['reason'], 'max_pnl_rs': 0}

def generate_conviction_report(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    target_date = pd.to_datetime(target_date_str).date()
    stock_data = {}
    
    for s in top_stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df = loader.load_data(days=25)
        df_5m, df_15m = resample_data(df, 5), resample_data(df, 15)
        df_5m['ema5_5m'], df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 5), talib.EMA(df_5m['close'].values.astype(float), 9)
        df_15m['ema5_15m'], df_15m['ema9_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5), talib.EMA(df_15m['close'].values.astype(float), 9)
        df['adx'] = talib.ADX(df['high'].values.astype(float), df['low'].values.astype(float), df['close'].values.astype(float), 14)
        df['st'] = talib.SMA(df['close'].values.astype(float), 10) # Proxy
        df = df.merge(df_5m[['date', 'ema5_5m', 'ema9_5m']], on='date', how='left').ffill()
        df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m']], on='date', how='left').ffill()
        
        df_day = df[df['date'].dt.date == target_date].reset_index(drop=True)
        mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
        df_day.attrs['orb'] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
        stock_data[s] = df_day

    engine = ConvictionEngine()
    engine.run_simulation(stock_data)
    df_res = pd.DataFrame(engine.all_trades)
    
    html_file = f"python-trader/backtest_lab/reports/conviction_report_{target_date_str}.html"
    total_pnl = pd.to_numeric(df_res['PnL_Rs'], errors='coerce').sum()
    
    with open(html_file, "w") as f:
        f.write(f"<html><body class='p-5 font-sans'><h1>💪 Professional Conviction Report (15m Structure)</h1>")
        f.write(f"<h2>Total PnL: Rs {total_pnl:,.2f} | 15m EMA Exit ACTIVE</h2>")
        f.write(df_res.to_html(classes='table table-striped table-bordered'))
        f.write("</body></html>")
    print(f"✅ Conviction Report generated: {html_file}")

if __name__ == "__main__":
    generate_conviction_report("2026-01-21")
