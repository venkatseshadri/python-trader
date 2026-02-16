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

class HarmonyTSLEngine:
    def __init__(self, top_n=5, tsl_activation=500, tsl_drop=25):
        self.top_n = top_n
        self.tsl_activation = tsl_activation
        self.tsl_drop = tsl_drop
        self.active_positions = {} 
        self.all_trades = []

    def run_simulation(self, stock_data_dict):
        stock_names = list(stock_data_dict.keys())
        max_len = len(stock_data_dict[stock_names[0]]['1m'])
        
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
                lot = LOT_SIZES.get(name, 50)
                
                # PNL Tracking
                pnl_pts = (ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)
                pnl_rs = pnl_pts * lot
                pos['max_pnl_rs'] = max(pos.get('max_pnl_rs', 0), pnl_rs)
                
                # EXIT CHECKS
                exit_hit = False
                reason = ""
                
                # 1. TSL Check
                if pos['max_pnl_rs'] >= self.tsl_activation:
                    allowed_drop = pos['max_pnl_rs'] * (self.tsl_drop / 100.0)
                    if pnl_rs <= (pos['max_pnl_rs'] - allowed_drop):
                        exit_hit, reason = True, f"TSL_HIT (Max:{pos['max_pnl_rs']:.0f})"
                
                # 2. Technical Exit
                if not exit_hit:
                    if (pos['type'] == 'LONG' and row['ema5_5m'] < row['ema9_5m']) or (pos['type'] == 'SHORT' and row['ema5_5m'] > row['ema9_5m']):
                        exit_hit, reason = True, "MTF_REVERSAL"
                
                # 3. EOD
                if not exit_hit and ts.time() >= dt_time(15, 15):
                    exit_hit, reason = True, "EOD"

                if exit_hit:
                    self.all_trades.append({
                        'Time': pos['entry_time'], 'Stock': name, 'Action': f"ENTRY ({pos['type']})",
                        'Price': pos['in'], 'PnL_Rs': '-', 'Reason': pos['logic']
                    })
                    self.all_trades.append({
                        'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_rs, 2), 'Reason': reason
                    })
                    to_close.append(name)
            
            for name in to_close: del self.active_positions[name]

            # Define current time from first stock
            curr_ts = stock_data_dict[stock_names[0]]['1m']['date'].iloc[i]
            if curr_ts.time() > dt_time(14,30): continue

            if len(self.active_positions) >= self.top_n: continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df_1m = stock_data_dict[name]['1m']
                if i < 1 or i >= len(df_1m): continue
                row = df_1m.iloc[i]
                
                is_long = (row['ema5_5m'] > row['ema9_5m']) and (row['ema5_15m'] > row['ema9_15m']) and (row['ema20_1m'] > row['ema50_1m'])
                is_short = (row['ema5_5m'] < row['ema9_5m']) and (row['ema5_15m'] < row['ema9_15m']) and (row['ema20_1m'] < row['ema50_1m'])
                
                side = None
                if is_long and orb_levels[name] and row['close'] > orb_levels[name]['h']: side = 'LONG'
                elif is_short and orb_levels[name] and row['close'] < orb_levels[name]['l']: side = 'SHORT'
                
                if side:
                    candidates.append({'name': name, 'side': side, 'ltp': row['close'], 'time': row['date']})

            ranked = sorted(candidates, key=lambda x: x['name'])[:self.top_n]
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {'in': c['ltp'], 'type': c['side'], 'entry_time': c['time'], 'logic': 'HARMONY_MTF', 'max_pnl_rs': 0}

def run_harmony_tsl_study(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    target_date = pd.to_datetime(target_date_str).date()
    
    stock_data = {}
    for s in top_stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df = loader.load_data(days=20)
        df_5m = resample_data(df, 5)
        df_15m = resample_data(df, 15)
        df_5m['ema5_5m'], df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 5), talib.EMA(df_5m['close'].values.astype(float), 9)
        df_15m['ema5_15m'], df_15m['ema9_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5), talib.EMA(df_15m['close'].values.astype(float), 9)
        df['ema20_1m'], df['ema50_1m'] = talib.EMA(df['close'].values.astype(float), 20), talib.EMA(df['close'].values.astype(float), 50)
        df = df.merge(df_5m[['date', 'ema5_5m', 'ema9_5m']], on='date', how='left').ffill()
        df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m']], on='date', how='left').ffill()
        stock_data[s] = {'1m': df[df['date'].dt.date == target_date].reset_index(drop=True)}

    results = []
    tsl_configs = [500, 750, 1000]
    
    print(f"🧪 Comparing TSL Activation Levels: {tsl_configs}...")
    
    for tsl_act in tsl_configs:
        print(f"▶️ Testing TSL Activation: Rs {tsl_act}")
        engine = HarmonyTSLEngine(top_n=5, tsl_activation=tsl_act, tsl_drop=25)
        engine.run_simulation(stock_data)
        
        df_res = pd.DataFrame(engine.all_trades)
        total_pnl = pd.to_numeric(df_res['PnL_Rs'], errors='coerce').sum()
        
        results.append({
            'TSL_Activation': tsl_act,
            'Total_PnL': total_pnl,
            'Trades': len(df_res) // 2 # Entry/Exit pairs
        })

    res_df = pd.DataFrame(results)
    print("\n" + "="*60)
    print("🏆 TSL ACTIVATION SENSITIVITY (Jan 21)")
    print("="*60)
    print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_harmony_tsl_study("2026-01-21")
