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

class PriceActionExitEngine:
    def __init__(self, top_n=5, exit_ema='ema5_5m'):
        self.top_n = top_n
        self.exit_ema_key = exit_ema
        self.active_positions = {} 
        self.all_trades = []

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
                
                # 🛡️ PRICE-ACTION MIRROR EXIT
                exit_ema_val = row[self.exit_ema_key]
                exit_hit = False
                if pos['type'] == 'LONG' and ltp < exit_ema_val:
                    exit_hit = True
                elif pos['type'] == 'SHORT' and ltp > exit_ema_val:
                    exit_hit = True
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    reason = f"PA_EXIT (LTP {'>' if pos['type']=='SHORT' else '<'} {self.exit_ema_key})" if exit_hit else "EOD"
                    pnl_pts = (ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)
                    self.all_trades.append({
                        'Time': pos['entry_time'], 'Stock': name, 'Action': f"ENTRY ({pos['type']})",
                        'Price': pos['in'], 'PnL_Rs': '-', 'Reason': 'HARMONY_MTF'
                    })
                    self.all_trades.append({
                        'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_pts * LOT_SIZES.get(name, 50), 2), 'Reason': reason
                    })
                    to_close.append(name)
            
            for name in to_close: del self.active_positions[name]

            curr_ts = stock_data_dict[stock_names[0]]['date'].iloc[i]
            if curr_ts.time() > dt_time(14, 30): continue
            if len(self.active_positions) >= self.top_n: continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df = stock_data_dict[name]
                if i < 1 or i >= len(df): continue
                row, prev = df.iloc[i], df.iloc[i-1]
                ltp = row['close']
                
                is_long = (row['ema5_5m'] > row['ema9_5m']) and (row['ema20_5m'] > row['ema50_5m']) and (row['adx'] > 20) and (row['adx'] > prev['adx'])
                is_short = (row['ema5_5m'] < row['ema9_5m']) and (row['ema20_5m'] < row['ema50_5m']) and (row['adx'] > 20) and (row['adx'] > prev['adx'])
                
                orb = df.attrs['orb']
                side = None
                if is_long and ltp > orb['h']: side = 'LONG'
                elif is_short and ltp < orb['l']: side = 'SHORT'
                if side: candidates.append({'name': name, 'side': side, 'ltp': ltp, 'time': row['date']})

            ranked = sorted(candidates, key=lambda x: x['name'])[:self.top_n]
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {'in': c['ltp'], 'type': c['side'], 'entry_time': c['time']}

def run_pa_exit_study(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    target_date = pd.to_datetime(target_date_str).date()
    stock_data = {}
    for s in top_stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df = loader.load_data(days=20)
        df_5m = resample_data(df, 5)
        df_5m['ema5_5m'], df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 5), talib.EMA(df_5m['close'].values.astype(float), 9)
        df['ema20_5m'] = talib.EMA(df['close'].values.astype(float), 100) # Proxy
        df['ema50_5m'] = talib.EMA(df['close'].values.astype(float), 250) # Proxy
        df['adx'] = talib.ADX(df['high'].values.astype(float), df['low'].values.astype(float), df['close'].values.astype(float), 14)
        df = df.merge(df_5m[['date', 'ema5_5m', 'ema9_5m']], on='date', how='left').ffill()
        df_day = df[df['date'].dt.date == target_date].reset_index(drop=True)
        mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
        df_day.attrs['orb'] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
        stock_data[s] = df_day

    for ema_key in ['ema5_5m', 'ema9_5m']:
        print(f"▶️ Testing Price-Action Exit vs {ema_key}...")
        engine = PriceActionExitEngine(top_n=5, exit_ema=ema_key)
        engine.run_simulation(stock_data)
        df_res = pd.DataFrame(engine.all_trades)
        if df_res.empty: continue
        total_pnl = pd.to_numeric(df_res['PnL_Rs'], errors='coerce').sum()
        html_file = f"python-trader/backtest_lab/reports/pa_exit_{ema_key}_{target_date_str}.html"
        with open(html_file, "w") as f:
            f.write(f"<html><body class='p-5'><h1>🛡️ Price-Action Mirror Exit (Close vs {ema_key})</h1><h2>Total PnL: Rs {total_pnl:,.2f}</h2>{df_res.to_html(classes='table')}</body></html>")
        print(f"✅ PA Report generated: {html_file}")

if __name__ == "__main__":
    run_pa_exit_study("2026-01-21")
