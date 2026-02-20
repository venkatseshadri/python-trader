import json
import os
import pandas as pd
import talib
import numpy as np
from datetime import datetime

def run_entry_comparison(file_list, symbol):
    results = []
    for file_path in file_list:
        try:
            with open(file_path, 'r') as f: data = json.load(f)
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # ORB Calc
            orb = df.between_time('09:15', '09:30')
            oh = orb['high'].max()
            
            # Resample for 15m EMA20 Exit
            base_time = df.index[0].replace(hour=9, minute=15, second=0)
            df_15 = df.resample('15min', origin=base_time).agg({'close':'last'}).dropna()
            df_15['EMA20'] = talib.EMA(df_15['close'].values, timeperiod=20)
            
            # Pre-calculate 1m EMA5 for Slope Guard
            df['EMA5'] = talib.EMA(df['close'].values, timeperiod=5)

            day_res = {'date': os.path.basename(file_path)}
            
            for mode in ['Naive', 'Guarded']:
                total_pnl = 0.0
                trades_count = 0
                in_pos = False
                entry_p = 0
                last_exit_t = None
                
                scan_data = df.between_time('09:31', '15:25')
                
                for t, row in scan_data.iterrows():
                    # 1. EXIT LOGIC (15m EMA20)
                    if in_pos:
                        idx_15 = df_15.index[df_15.index < t]
                        if len(idx_15) >= 1:
                            ema_val = df_15.loc[idx_15[-1], 'EMA20']
                            if not pd.isna(ema_val) and row['close'] < ema_val:
                                # Exit
                                pnl = (row['close'] - entry_p) / entry_p * 100
                                total_pnl += pnl
                                in_pos = False
                                last_exit_t = t
                                continue

                    # 2. ENTRY LOGIC
                    if not in_pos:
                        # Base condition
                        if row['close'] > oh:
                            
                            if mode == 'Guarded':
                                # Cooldown Check (30 mins)
                                if last_exit_t and (t - last_exit_t).total_seconds() < 1800:
                                    continue
                                
                                # Slope Guard (EMA5 rising)
                                prev_t = t - pd.Timedelta(minutes=5)
                                if prev_t in df.index:
                                    if df.loc[t, 'EMA5'] <= df.loc[prev_t, 'EMA5']:
                                        continue
                                
                                # Freshness Guard (Near Day High)
                                day_high_so_far = df.loc[:t, 'high'].max()
                                if row['close'] < day_high_so_far * 0.998: # Must be within 0.2% of high
                                    continue

                            # Enter Trade
                            entry_p = row['close']
                            in_pos = True
                            trades_count += 1
                
                # Close at EOD if still open
                if in_pos:
                    pnl = (df['close'].iloc[-1] - entry_p) / entry_p * 100
                    total_pnl += pnl
                
                day_res[f'{mode}_pnl'] = total_pnl
                day_res[f'{mode}_trades'] = trades_count

            results.append(day_res)
        except: continue
    return pd.DataFrame(results)

if __name__ == "__main__":
    for sym in ["ADANIENT", "SBIN"]:
        bp = f"backtest_lab/data/intraday1pct/{sym}/"
        all_fs = [os.path.join(bp, f) for f in sorted(os.listdir(bp)) if f.endswith('.json')]
        fs = all_fs[-100:]
        
        print(f"\n🔬 Entry Guard Study: {sym} (100 Days)")
        df = run_entry_comparison(fs, sym)
        
        if not df.empty:
            summary = []
            for mode in ['Naive', 'Guarded']:
                summary.append({
                    'Strategy': mode,
                    'Avg PnL %': df[f'{mode}_pnl'].mean(),
                    'Total Trades': df[f'{mode}_trades'].sum(),
                    'Avg Trades/Day': df[f'{mode}_trades'].mean(),
                    'Win Rate %': (df[f'{mode}_pnl'] > 0).sum() / len(df) * 100
                })
            print(pd.DataFrame(summary).to_string(index=False))
