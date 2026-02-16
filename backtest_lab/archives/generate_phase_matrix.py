import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.generate_ultra_matrix import resample_data, LOT_SIZES

class PhaseDefenseEngine:
    def __init__(self, top_n=5):
        self.top_n = top_n
        self.active_positions = {} 
        self.all_trades = []

    def run_simulation(self, stock_data_dict):
        stock_names = list(stock_data_dict.keys())
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
                reason = ""
                
                # 🛡️ PHASE 2: PROTECT MOJO (If profit hit 500, use 1m vs 5m EMA9)
                if pos['max_pnl_rs'] >= 500:
                    e9_5m = row['ema9_5m']
                    if (pos['type'] == 'LONG' and ltp < e9_5m) or (pos['type'] == 'SHORT' and ltp > e9_5m):
                        exit_hit, reason = True, f"BRAKE (LTP vs 5m_EMA9)"
                
                # 🛡️ PHASE 1: INITIAL DEFENSE (Always exit on 15m structural break)
                if not exit_hit:
                    if (pos['type'] == 'LONG' and row['ema5_15m'] < row['ema9_15m']) or (pos['type'] == 'SHORT' and row['ema5_15m'] > row['ema9_15m']):
                        exit_hit, reason = True, "STRUCTURAL_REVERSAL"
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    self.all_trades.append({'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF', 'PnL_Rs': round(pnl_rs, 2), 'Reason': reason if exit_hit else "EOD"})
                    to_close.append(name)
            for name in to_close: del self.active_positions[name]

            curr_ts = stock_data_dict[stock_names[0]]['date'].iloc[i]
            if curr_ts.minute % 15 != 0: continue
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df = stock_data_dict[name]
                row = df.iloc[i]
                is_long = (row['ema5_15m'] > row['ema9_15m']) and (row['ema20_15m'] > row['ema50_15m']) and (row['adx_15m'] > 20)
                is_short = (row['ema5_15m'] < row['ema9_15m']) and (row['ema20_15m'] < row['ema50_15m']) and (row['adx_15m'] > 20)
                orb = df.attrs['orb']
                side = 'LONG' if is_long and row['close'] > orb['h'] else ('SHORT' if is_short and row['close'] < orb['l'] else None)
                if side: candidates.append({'name': name, 'side': side, 'ltp': row['close'], 'time': curr_ts})
            ranked = sorted(candidates, key=lambda x: x['name'])[:self.top_n]
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {'in': c['ltp'], 'type': c['side'], 'entry_time': c['time'], 'max_pnl_rs': 0}

def generate_phase_matrix():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    sample_df = pd.read_csv(os.path.join(stocks_dir, "RELIANCE_minute.csv"))
    all_dates = sorted(pd.to_datetime(sample_df['date']).dt.date.unique())[-7:]
    
    matrix_data = {s: {d.strftime('%d-%b'): 0 for d in all_dates} for s in top_stocks}
    engine = PhaseDefenseEngine(top_n=5)
    
    for d in all_dates:
        print(f"▶️ Simulating: {d}")
        stock_data_day = {}
        for s in top_stocks:
            loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
            df = loader.load_data(days=20)
            df_5m, df_15m = resample_data(df, 5), resample_data(df, 15)
            df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 9)
            df_15m['ema5_15m'], df_15m['ema9_15m'], df_15m['ema20_15m'], df_15m['ema50_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5), talib.EMA(df_15m['close'].values.astype(float), 9), talib.EMA(df_15m['close'].values.astype(float), 20), talib.EMA(df_15m['close'].values.astype(float), 50)
            df_15m['adx_15m'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
            df = df.merge(df_5m[['date', 'ema9_5m']], on='date', how='left').ffill()
            df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m', 'ema20_15m', 'ema50_15m', 'adx_15m']], on='date', how='left').ffill()
            df_day = df[df['date'].dt.date == d].reset_index(drop=True)
            if df_day.empty: continue
            mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
            df_day.attrs['orb'] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
            stock_data_day[s] = df_day
        
        engine.run_simulation(stock_data_day)
        for t in engine.all_trades:
            matrix_data[t['Stock']][d.strftime('%d-%b')] += t['PnL_Rs']
        engine.all_trades = []

    df_matrix = pd.DataFrame.from_dict(matrix_data, orient='index')
    df_matrix['Total'] = df_matrix.sum(axis=1)
    df_matrix.to_html("python-trader/backtest_lab/reports/phase_defense_matrix.html")
    print(f"✅ Phase Matrix generated: python-trader/backtest_lab/reports/phase_defense_matrix.html")

if __name__ == "__main__":
    generate_phase_matrix()
