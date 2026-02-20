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
LOT_SIZES = {"RELIANCE": 250, "TCS": 175, "LT": 175, "SBIN": 750, "HDFCBANK": 550, "INFY": 400, "ICICIBANK": 700, "AXISBANK": 625, "BHARTIARTL": 475, "KOTAKBANK": 400, "BOSCHLTD": 25}

def resample_data(df, interval_min):
    df = df.set_index('date')
    resampled = df.resample(f'{interval_min}min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    return resampled.reset_index()

class UltraDefenseEngine:
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
                # 🛡️ ULTRA FAST BRAKE (1m LTP vs 5m EMA5)
                e5_5m = row['ema5_5m']
                if (pos['type'] == 'LONG' and ltp < e5_5m) or (pos['type'] == 'SHORT' and ltp > e5_5m):
                    exit_hit, reason = True, f"1m_PRICE_VS_5m_EMA5 ({ltp:.1f} vs {e5_5m:.1f})"
                
                # 🛡️ PROFIT LOCK (70% Retention)
                if not exit_hit and pos['max_pnl_rs'] >= 500:
                    if pnl_rs <= (pos['max_pnl_rs'] * 0.70):
                        exit_hit, reason = True, f"TSL_LOCK (Max:{pos['max_pnl_rs']:.0f})"
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    if not exit_hit: reason = "EOD"
                    self.all_trades.append({'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF', 'PnL_Rs': round(pnl_rs, 2), 'Reason': reason})
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

def generate_ultra_matrix():
    stocks_dir = "backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK", "BOSCHLTD", "ABB", "ADANIENT", "ASIANPAINT", "BAJFINANCE"]
    sample_df = pd.read_csv(os.path.join(stocks_dir, "RELIANCE_minute.csv"))
    all_dates = sorted(pd.to_datetime(sample_df['date']).dt.date.unique())[-7:]
    
    matrix_data = {s: {d.strftime('%d-%b'): 0 for d in all_dates} for s in top_stocks}
    engine = UltraDefenseEngine(top_n=5)
    
    for d in all_dates:
        print(f"▶️ Simulating: {d}")
        stock_data_day = {}
        for s in top_stocks:
            loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
            df = loader.load_data(days=20)
            df_5m, df_15m = resample_data(df, 5), resample_data(df, 15)
            df_5m['ema5_5m'] = talib.EMA(df_5m['close'].values.astype(float), 5)
            df_15m['ema5_15m'], df_15m['ema9_15m'], df_15m['ema20_15m'], df_15m['ema50_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5), talib.EMA(df_15m['close'].values.astype(float), 9), talib.EMA(df_15m['close'].values.astype(float), 20), talib.EMA(df_15m['close'].values.astype(float), 50)
            df_15m['adx_15m'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
            df = df.merge(df_5m[['date', 'ema5_5m']], on='date', how='left').ffill()
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
    df_matrix.to_html("backtest_lab/reports/ultra_defense_matrix.html")
    print(f"✅ Ultra Matrix generated: backtest_lab/reports/ultra_defense_matrix.html")

if __name__ == "__main__":
    generate_ultra_matrix()
