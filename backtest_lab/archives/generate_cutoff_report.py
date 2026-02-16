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

class CutoffEngine:
    def __init__(self, top_n=5, entry_cutoff=dt_time(11, 0)):
        self.top_n = top_n
        self.entry_cutoff = entry_cutoff
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
                pnl_pts = (ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)
                pnl_rs = pnl_pts * lot
                pos['max_pnl_rs'] = max(pos.get('max_pnl_rs', 0), pnl_rs)
                
                exit_hit = False
                if pos['max_pnl_rs'] >= 500:
                    if pnl_rs <= (pos['max_pnl_rs'] * 0.70):
                        exit_hit, reason = True, f"TSL_GUARD (Max:{pos['max_pnl_rs']:.0f})"
                
                if not exit_hit:
                    if (pos['type'] == 'LONG' and row['ema5_15m'] < row['ema9_15m']) or (pos['type'] == 'SHORT' and row['ema5_15m'] > row['ema9_15m']):
                        exit_hit, reason = True, "15m_STRUCTURAL_REVERSAL"
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    if not exit_hit: reason = "EOD"
                    self.all_trades.append({'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF', 'PnL_Rs': round(pnl_rs, 2), 'Reason': reason})
                    to_close.append(name)
            for name in to_close: del self.active_positions[name]

            curr_ts = stock_data_dict[stock_names[0]]['date'].iloc[i]
            # 🛡️ THE GOLDEN CUTOFF
            if curr_ts.time() > self.entry_cutoff: continue
            if curr_ts.minute % 15 != 0: continue
            if len(self.active_positions) >= self.top_n: continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df = stock_data_dict[name]
                if i < 1 or i >= len(df): continue
                row, prev = df.iloc[i], df.iloc[i-1]
                is_short = (row['ema5_15m'] < row['ema9_15m']) and (row['ema20_15m'] < row['ema50_15m'])
                is_fresh = (row['adx_15m'] > 20) and (row['adx_15m'] > prev['adx_15m'])
                orb = df.attrs['orb']
                if is_short and is_fresh and row['close'] < orb['l']:
                    candidates.append({'name': name, 'side': 'SHORT', 'ltp': row['close'], 'time': curr_ts})

            ranked = sorted(candidates, key=lambda x: x['name'])[:self.top_n]
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {'in': c['ltp'], 'type': c['side'], 'entry_time': c['time'], 'max_pnl_rs': 0}

def run_cutoff_study(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    target_date = pd.to_datetime(target_date_str).date()
    stock_data = {}
    for s in top_stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df = loader.load_data(days=20)
        df_15m = resample_data(df, 15)
        df_15m['ema5_15m'], df_15m['ema9_15m'], df_15m['ema20_15m'], df_15m['ema50_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5), talib.EMA(df_15m['close'].values.astype(float), 9), talib.EMA(df_15m['close'].values.astype(float), 20), talib.EMA(df_15m['close'].values.astype(float), 50)
        df_15m['adx_15m'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
        df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m', 'ema20_15m', 'ema50_15m', 'adx_15m']], on='date', how='left').ffill()
        df_day = df[df['date'].dt.date == target_date].reset_index(drop=True)
        mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
        df_day.attrs['orb'] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
        stock_data[s] = df_day

    results = []
    for cutoff in [dt_time(11, 0), dt_time(11, 30), dt_time(12, 0)]:
        engine = CutoffEngine(entry_cutoff=cutoff)
        engine.run_simulation(stock_data)
        pnl = sum(pd.to_numeric([t['PnL_Rs'] for t in engine.all_trades], errors='coerce'))
        results.append({'Cutoff': cutoff.strftime("%H:%M"), 'PnL': pnl, 'Trades': len(engine.all_trades)})

    print("\n" + "="*60)
    print("🏆 ENTRY CUTOFF SENSITIVITY (Jan 21)")
    print("="*60)
    print(pd.DataFrame(results).to_string(index=False))

if __name__ == "__main__":
    run_cutoff_study("2026-01-21")
