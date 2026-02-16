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

class FullDefenseEngine:
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
                row, prev = df.iloc[i], df.iloc[i-1]
                ltp, ts = row['close'], row['date']
                lot = LOT_SIZES.get(name, 50)
                pnl_rs = ((ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)) * lot
                pos['max_pnl_rs'] = max(pos.get('max_pnl_rs', 0), pnl_rs)
                
                exit_hit = False
                reason = ""
                
                # 🛡️ 1. EMERGENCY BRAKE (1m LTP vs 5m EMA9)
                e9_5m = row['ema9_5m']
                if (pos['type'] == 'LONG' and ltp < e9_5m) or (pos['type'] == 'SHORT' and ltp > e9_5m):
                    exit_hit, reason = True, f"1m_PRICE_VS_5m_EMA9 ({ltp:.1f} vs {e9_5m:.1f})"
                
                # 🛡️ 2. MOJO LOSS (ADX Falling)
                if not exit_hit and row['adx_15m'] < prev['adx_15m'] and row['adx_15m'] < 25:
                    exit_hit, reason = True, f"MOJO_LOSS (ADX Falling: {row['adx_15m']:.1f})"
                
                # 🛡️ 3. TSL GUARD (Profit Protection)
                if not exit_hit and pos['max_pnl_rs'] >= 500:
                    if pnl_rs <= (pos['max_pnl_rs'] * 0.70):
                        exit_hit, reason = True, f"TSL_LOCK (70% Retained | Max:{pos['max_pnl_rs']:.0f})"
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    if not exit_hit: reason = "EOD"
                    self.all_trades.append({
                        'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_rs, 2), 'Reason': reason
                    })
                    to_close.append(name)
            for name in to_close: del self.active_positions[name]

            # ENTRY LOGIC (15m Interval)
            curr_ts = stock_data_dict[stock_names[0]]['date'].iloc[i]
            if curr_ts.minute % 15 != 0: continue
            if curr_ts.time() > dt_time(14,30): continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df = stock_data_dict[name]
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

def audit_full_defense_bosch():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    loader = DataLoader(os.path.join(stocks_dir, "BOSCHLTD_minute.csv"))
    df = loader.load_data(days=30)
    
    df_5m = resample_data(df, 5)
    df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 9)
    
    df_15m = resample_data(df, 15)
    df_15m['ema5_15m'], df_15m['ema9_15m'], df_15m['ema20_15m'], df_15m['ema50_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5), talib.EMA(df_15m['close'].values.astype(float), 9), talib.EMA(df_15m['close'].values.astype(float), 20), talib.EMA(df_15m['close'].values.astype(float), 50)
    df_15m['adx_15m'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
    
    df = df.merge(df_5m[['date', 'ema9_5m']], on='date', how='left').ffill()
    df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m', 'ema20_15m', 'ema50_15m', 'adx_15m']], on='date', how='left').ffill()
    
    target_date = pd.to_datetime('2026-01-14').date()
    df_day = df[df['date'].dt.date == target_date].reset_index(drop=True)
    mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
    df_day.attrs['orb'] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
    
    engine = FullDefenseEngine(top_n=5)
    engine.run_simulation({"BOSCHLTD": df_day})
    
    print("\n" + "="*80)
    print(f"🛡️ FULL DEFENSE AUDIT: BOSCHLTD {target_date}")
    print("="*80)
    print(pd.DataFrame(engine.all_trades).to_string(index=False))

if __name__ == "__main__":
    audit_full_defense_bosch()
