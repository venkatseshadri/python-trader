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

class FullSpectrumEngine:
    def __init__(self, top_n=5, threshold=0.35):
        self.top_n = top_n
        self.threshold = threshold
        self.active_positions = {} 
        self.all_trades = []

    def run_simulation(self, stock_data_dict):
        stock_names = list(stock_data_dict.keys())
        max_len = len(stock_data_dict[stock_names[0]]['1m'])
        
        # 1. ORB
        orb_levels = {}
        for name in stock_names:
            df_1m = stock_data_dict[name]['1m']
            mask = (df_1m['date'].dt.time >= dt_time(9, 15)) & (df_1m['date'].dt.time <= dt_time(10, 0))
            if not df_1m.empty and mask.any():
                orb_levels[name] = {'h': df_1m.loc[mask, 'high'].max(), 'l': df_1m.loc[mask, 'low'].min()}
            else: orb_levels[name] = None

        for i in range(45, max_len):
            to_close = []
            for name, pos in self.active_positions.items():
                df_1m = stock_data_dict[name]['1m']
                if i >= len(df_1m): continue
                row = df_1m.iloc[i]
                ltp, ts = row['close'], row['date']
                
                # Exit on 5m EMA Reversal (Safety)
                exit_hit = (pos['type'] == 'LONG' and row['ema5_5m'] < row['ema9_5m']) or (pos['type'] == 'SHORT' and row['ema5_5m'] > row['ema9_5m'])
                if exit_hit or ts.time() >= dt_time(15, 15):
                    pnl_pts = (ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)
                    self.all_trades.append({
                        'Time': pos['entry_time'], 'Stock': name, 'Action': f"ENTRY ({pos['type']})",
                        'Price': pos['in'], 'PnL_Rs': '-', 'Reason': pos['entry_logic']
                    })
                    self.all_trades.append({
                        'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_pts * LOT_SIZES.get(name, 50), 2), 
                        'Reason': f"MTF_REVERSAL | E5_5m: {row['ema5_5m']:.1f}"
                    })
                    to_close.append(name)
            
            for name in to_close: del self.active_positions[name]

            if len(self.active_positions) >= self.top_n: continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df_1m = stock_data_dict[name]['1m']
                if i < 1 or i >= len(df_1m): continue
                
                row = df_1m.iloc[i]
                # 🛡️ FULL-SPECTRUM ALIGNMENT CHECK
                is_long_aligned = (row['ema5_5m'] > row['ema9_5m']) and (row['ema5_15m'] > row['ema9_15m']) and (row['ema20_1m'] > row['ema50_1m'])
                is_short_aligned = (row['ema5_5m'] < row['ema9_5m']) and (row['ema5_15m'] < row['ema9_15m']) and (row['ema20_1m'] < row['ema50_1m'])
                
                if not (is_long_aligned or is_short_aligned): continue
                
                # Check ORB Breakout
                side = None
                if is_long_aligned and orb_levels[name] and row['close'] > orb_levels[name]['h']: side = 'LONG'
                elif is_short_aligned and orb_levels[name] and row['close'] < orb_levels[name]['l']: side = 'SHORT'
                
                if side:
                    logic = f"5m:{is_long_aligned if side=='LONG' else is_short_aligned} | 15m:YES | 20/50:YES"
                    candidates.append({'name': name, 'side': side, 'ltp': row['close'], 'time': row['date'], 'logic': logic})

            ranked = sorted(candidates, key=lambda x: x['name'])[:self.top_n] # Simple alpha sort for this deep-dive
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {'in': c['ltp'], 'type': c['side'], 'entry_time': c['time'], 'entry_logic': c['logic']}

def run_full_spectrum_study(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    target_date = pd.to_datetime(target_date_str).date()
    
    stock_data = {}
    for s in top_stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df_1m = loader.load_data(days=20) # More days for EMA 50
        
        # MTF Prep
        df_5m = resample_data(df_1m, 5)
        df_15m = resample_data(df_1m, 15)
        
        # 5m Indicators
        df_5m['ema5_5m'] = talib.EMA(df_5m['close'].values.astype(float), 5)
        df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 9)
        # 15m Indicators
        df_15m['ema5_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5)
        df_15m['ema9_15m'] = talib.EMA(df_15m['close'].values.astype(float), 9)
        # 1m Long-term
        df_1m['ema20_1m'] = talib.EMA(df_1m['close'].values.astype(float), 20)
        df_1m['ema50_1m'] = talib.EMA(df_1m['close'].values.astype(float), 50)
        
        # Merge
        df_1m = df_1m.merge(df_5m[['date', 'ema5_5m', 'ema9_5m']], on='date', how='left').ffill()
        df_1m = df_1m.merge(df_15m[['date', 'ema5_15m', 'ema9_15m']], on='date', how='left').ffill()
        
        stock_data[s] = {'1m': df_1m[df_1m['date'].dt.date == target_date].reset_index(drop=True)}

    engine = FullSpectrumEngine(top_n=5)
    engine.run_simulation(stock_data)
    
    df_res = pd.DataFrame(engine.all_trades)
    
    # Generate HTML
    total_pnl = pd.to_numeric(df_res['PnL_Rs'], errors='coerce').sum()
    html_file = f"python-trader/backtest_lab/reports/full_spectrum_harmony_{target_date_str}.html"
    
    html_content = f"<html><body style='padding:50px; font-family:sans-serif;'>"
    html_content += f"<h1>🌈 Full-Spectrum Harmony Report (5m/15m/1m Alignment)</h1>"
    html_content += f"<h2>Target Date: {target_date_str} | Total Portfolio PnL: Rs {total_pnl:,.2f}</h2>"
    html_content += df_res.to_html(classes='table table-striped')
    html_content += "</body></html>"
    
    with open(html_file, "w") as f:
        f.write(html_content)
    print(f"✅ Full-Spectrum Report generated: {html_file}")

if __name__ == "__main__":
    run_full_spectrum_study("2026-01-21")
