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

class GoldenWeekEngine:
    def __init__(self, top_n=5):
        self.top_n = top_n
        self.active_positions = {} 
        self.all_trades = []

    def run_simulation(self, stock_data_dict):
        stock_names = list(stock_data_dict.keys())
        # Use the minimum length across all stocks to avoid IndexOutOfBounds
        max_len = min(len(df) for df in stock_data_dict.values())
        
        for i in range(45, max_len):
            to_close = []
            for name, pos in self.active_positions.items():
                df = stock_data_dict[name]
                if i >= len(df): continue
                row = df.iloc[i]
                ltp, ts = row['close'], row['date']
                lot = LOT_SIZES.get(name, 50)
                pnl_rs = ((ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)) * lot
                pos['max_pnl_rs'] = max(pos.get('max_pnl_rs', 0), pnl_rs)
                
                exit_hit = False
                # 1. 1m TSL (Rs 500 / 30%)
                if pos['max_pnl_rs'] >= 500:
                    if pnl_rs <= (pos['max_pnl_rs'] * 0.70):
                        exit_hit, reason = True, "TSL_GUARD"
                # 2. 15m Structural Crossover (Checking every 1m)
                if not exit_hit:
                    if (pos['type'] == 'LONG' and row['ema5_15m'] < row['ema9_15m']) or (pos['type'] == 'SHORT' and row['ema5_15m'] > row['ema9_15m']):
                        exit_hit, reason = True, "15m_STRUCTURAL_REVERSAL"
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    self.all_trades.append({'Time': pos['entry_time'], 'Stock': name, 'Action': f"ENTRY ({pos['type']})", 'Price': pos['in'], 'PnL_Rs': '-', 'Reason': 'HARMONY_MTF'})
                    self.all_trades.append({'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF', 'Price': ltp, 'PnL_Rs': round(pnl_rs, 2), 'Reason': reason if exit_hit else "EOD"})
                    to_close.append(name)
            for name in to_close: del self.active_positions[name]

            curr_ts = stock_data_dict[stock_names[0]]['date'].iloc[i]
            if curr_ts.minute % 15 != 0: continue
            if curr_ts.time() > dt_time(14, 30): continue
            if len(self.active_positions) >= self.top_n: continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df = stock_data_dict[name]
                if i < 1 or i >= len(df): continue
                row, prev = df.iloc[i], df.iloc[i-1]
                is_long = (row['ema5_15m'] > row['ema9_15m']) and (row['ema20_15m'] > row['ema50_15m']) and (row['adx_15m'] > 20)
                is_short = (row['ema5_15m'] < row['ema9_15m']) and (row['ema20_15m'] < row['ema50_15m']) and (row['adx_15m'] > 20)
                orb = df.attrs['orb']
                side = None
                if is_long and row['close'] > orb['h']: side = 'LONG'
                elif is_short and row['close'] < orb['l']: side = 'SHORT'
                if side: candidates.append({'name': name, 'side': side, 'ltp': row['close'], 'time': curr_ts})

            ranked = sorted(candidates, key=lambda x: x['name'])[:self.top_n]
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {'in': c['ltp'], 'type': c['side'], 'entry_time': c['time'], 'max_pnl_rs': 0}

def run_golden_week():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    sample_df = pd.read_csv(os.path.join(stocks_dir, "RELIANCE_minute.csv"))
    sample_df['date'] = pd.to_datetime(sample_df['date'])
    all_dates = sorted(sample_df['date'].dt.date.unique())
    golden_week_dates = all_dates[-7:]
    
    print(f"🔬 Running Golden Week Study: {golden_week_dates[0]} to {golden_week_dates[-1]}")
    engine = GoldenWeekEngine(top_n=5)
    
    for d in golden_week_dates:
        print(f"▶️ Simulating: {d}")
        stock_data_day = {}
        for s in top_stocks:
            loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
            df = loader.load_data(days=20)
            df_15m = resample_data(df, 15)
            df_15m['ema5_15m'], df_15m['ema9_15m'], df_15m['ema20_15m'], df_15m['ema50_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5), talib.EMA(df_15m['close'].values.astype(float), 9), talib.EMA(df_15m['close'].values.astype(float), 20), talib.EMA(df_15m['close'].values.astype(float), 50)
            df_15m['adx_15m'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
            df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m', 'ema20_15m', 'ema50_15m', 'adx_15m']], on='date', how='left').ffill()
            df_day = df[df['date'].dt.date == d].reset_index(drop=True)
            if df_day.empty: continue
            mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
            df_day.attrs['orb'] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
            stock_data_day[s] = df_day
        engine.run_simulation(stock_data_day)

    df_res = pd.DataFrame(engine.all_trades)
    html_file = "python-trader/backtest_lab/reports/golden_week_report.html"
    total_pnl = pd.to_numeric(df_res['PnL_Rs'], errors='coerce').sum() if not df_res.empty else 0
    with open(html_file, "w") as f:
        f.write(f"<html><body class='p-5 font-sans'><h1>🌟 NIFTY 50 GOLDEN WEEK REPORT</h1>")
        f.write(f"<h2>Total Portfolio PnL: Rs {total_pnl:,.2f}</h2>")
        if not df_res.empty: f.write(df_res.to_html(classes='table table-striped'))
        else: f.write("<h3>No trades taken.</h3>")
        f.write("</body></html>")
    print(f"✅ GOLDEN WEEK Report generated: {html_file}")

if __name__ == "__main__":
    os.makedirs("python-trader/backtest_lab/reports", exist_ok=True)
    run_golden_week()
