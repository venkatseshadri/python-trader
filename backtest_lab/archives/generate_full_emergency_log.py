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

class FullLogEmergencyEngine:
    def __init__(self, top_n=5):
        self.top_n = top_n
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
                lot = LOT_SIZES.get(name, 50)
                pnl_rs = ((ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)) * lot
                
                # 🛡️ EMERGENCY BRAKE
                e9_5m = row['ema9_5m']
                exit_hit = (pos['type'] == 'LONG' and ltp < e9_5m) or (pos['type'] == 'SHORT' and ltp > e9_5m)
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    reason = f"EMERGENCY_BRAKE (LTP vs E9_5m:{e9_5m:.1f})" if exit_hit else "EOD"
                    
                    # Log ENTRY
                    self.all_trades.append({
                        'Time': pos['entry_time'], 'Stock': name, 'Action': f"ENTRY ({pos['type']})",
                        'Price': pos['in'], 'PnL_Rs': '-', 'Reason': pos['logic']
                    })
                    # Log EXIT
                    self.all_trades.append({
                        'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_rs, 2), 'Reason': reason
                    })
                    to_close.append(name)
            for name in to_close: del self.active_positions[name]

            curr_ts = stock_data_dict[stock_names[0]]['date'].iloc[i]
            if curr_ts.minute % 15 != 0: continue
            if curr_ts.time() > dt_time(14,30): continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df = stock_data_dict[name]
                if i < 1 or i >= len(df): continue
                row, prev = df.iloc[i], df.iloc[i-1]
                
                # MOJO Shield Logic
                is_afternoon = curr_ts.time() > dt_time(11, 0)
                adx_threshold = 30 if is_afternoon else 20
                if (row['adx_15m'] > adx_threshold) and (row['adx_15m'] > prev['adx_15m']):
                    is_short = (row['ema5_15m'] < row['ema9_15m']) and (row['ema20_15m'] < row['ema50_15m'])
                    orb = df.attrs['orb']
                    if is_short and row['close'] < orb['l']:
                        logic = f"ADX:{row['adx_15m']:.1f} | 15m_Harmony:OK"
                        candidates.append({'name': name, 'side': 'SHORT', 'ltp': row['close'], 'time': curr_ts, 'logic': logic})

            ranked = sorted(candidates, key=lambda x: x['name'])[:self.top_n]
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {'in': c['ltp'], 'type': c['side'], 'entry_time': c['time'], 'logic': c['logic']}

def generate_full_emergency_report(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    target_date = pd.to_datetime(target_date_str).date()
    stock_data = {}
    for s in top_stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df = loader.load_data(days=30)
        df_5m = resample_data(df, 5)
        df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 9)
        df_15m = resample_data(df, 15)
        df_15m['ema5_15m'], df_15m['ema9_15m'], df_15m['ema20_15m'], df_15m['ema50_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5), talib.EMA(df_15m['close'].values.astype(float), 9), talib.EMA(df_15m['close'].values.astype(float), 20), talib.EMA(df_15m['close'].values.astype(float), 50)
        df_15m['adx_15m'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
        df = df.merge(df_5m[['date', 'ema9_5m']], on='date', how='left').ffill()
        df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m', 'ema20_15m', 'ema50_15m', 'adx_15m']], on='date', how='left').ffill()
        df_day = df[df['date'].dt.date == target_date].reset_index(drop=True)
        mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
        df_day.attrs['orb'] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
        stock_data[s] = df_day

    engine = FullLogEmergencyEngine()
    engine.run_simulation(stock_data)
    df_res = pd.DataFrame(engine.all_trades)
    total_pnl = pd.to_numeric(df_res['PnL_Rs'], errors='coerce').sum() if not df_res.empty else 0
    html_file = f"python-trader/backtest_lab/reports/full_emergency_log_{target_date_str}.html"
    
    with open(html_file, "w") as f:
        f.write(f"<html><head><link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'></head>")
        f.write(f"<body class='p-5 font-sans'><h1>🧾 Full Transaction Log: Emergency Brake Strategy</h1>")
        f.write(f"<h2>Total PnL: Rs {total_pnl:,.2f}</h2>")
        if not df_res.empty: f.write(df_res.to_html(classes='table table-sm table-striped table-bordered'))
        else: f.write("<h3>No trades found.</h3>")
        f.write("</body></html>")
    print(f"✅ Full Log Report generated: {html_file}")

if __name__ == "__main__":
    generate_full_emergency_report("2026-01-21")
