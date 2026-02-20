import json
import os
import pandas as pd
import talib
import numpy as np
from datetime import datetime

def calculate_st_manual(df, period=10, multiplier=2.0): # More sensitive multiplier
    high, low, close = df['high'].values, df['low'].values, df['close'].values
    atr = talib.ATR(high, low, close, timeperiod=period)
    hl2 = (high + low) / 2
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    final_ub, final_lb = np.copy(upper_band), np.copy(lower_band)
    st = np.zeros(len(df))
    for i in range(1, len(df)):
        final_ub[i] = upper_band[i] if upper_band[i] < final_ub[i-1] or close[i-1] > final_ub[i-1] else final_ub[i-1]
        final_lb[i] = lower_band[i] if lower_band[i] > final_lb[i-1] or close[i-1] < final_lb[i-1] else final_lb[i-1]
    st[0] = final_ub[0]
    for i in range(1, len(df)):
        if st[i-1] == final_ub[i-1]:
            st[i] = final_ub[i] if close[i] <= final_ub[i] else final_lb[i]
        else:
            st[i] = final_lb[i] if close[i] >= final_lb[i] else final_ub[i]
    return pd.Series(st, index=df.index)

def run_study(file_list):
    results = []
    for file_path in file_list:
        try:
            with open(file_path, 'r') as f: data = json.load(f)
            df_1m = pd.DataFrame(data)
            df_1m['date'] = pd.to_datetime(df_1m['date'])
            df_1m.set_index('date', inplace=True)
            
            # ORB Calc
            orb = df_1m.between_time('09:15', '09:30')
            if orb.empty: continue
            oh = orb['high'].max()
            
            # Entry
            post = df_1m.between_time('09:31', '15:30')
            ent = post[post['close'] > oh]
            if ent.empty: continue
            et, ep = ent.index[0], oh
            
            day_results = {'date': os.path.basename(file_path)}
            for tf in ['1min', '5min', '10min', '15min']:
                # Resample starting from fixed market open to align buckets
                base_time = df_1m.index[0].replace(hour=9, minute=15, second=0)
                df_tf = df_1m.resample(tf, origin=base_time).agg({'high':'max','low':'min','close':'last'}).dropna()
                
                if len(df_tf) < 11: # Reduced requirement slightly for shorter days
                    day_results[f'{tf}_pnl'] = (df_1m['close'].iloc[-1] - ep) / ep * 100
                    day_results[f'{tf}_time'] = df_1m.index[-1].strftime('%H:%M')
                    continue

                df_tf['ST'] = calculate_st_manual(df_tf)
                trd = df_1m.loc[et:]; ex_p = df_1m['close'].iloc[-1]; ex_t = df_1m.index[-1]
                
                for t, row in trd.iterrows():
                    # Correct lookback: use the most recent CLOSED candle of the timeframe
                    idx = df_tf.index[df_tf.index < t] # Changed <= to < to avoid lookahead
                    if len(idx) < 1: continue
                    sv = df_tf.loc[idx[-1], 'ST'] # Last closed ST
                    if not pd.isna(sv) and row['close'] < sv: 
                        ex_p = row['close']
                        ex_t = t
                        break
                day_results[f'{tf}_pnl'] = (ex_p - ep) / ep * 100
                day_results[f'{tf}_time'] = ex_t.strftime('%H:%M')
            
            day_results['EOD_pnl'] = (df_1m['close'].iloc[-1] - ep) / ep * 100
            results.append(day_results)
        except: continue
    return pd.DataFrame(results)

if __name__ == "__main__":
    for sym in ["ADANIENT", "ABB", "BEL"]:
        bp = f"backtest_lab/data/intraday1pct/{sym}/"
        if not os.path.exists(bp): continue
        fs = [os.path.join(bp, f) for f in sorted(os.listdir(bp)) if f.endswith('.json')][-50:]
        
        print(f"\n🔬 Study: {sym} (Last 50 Days, ST 10, 2.0)")
        df = run_study(fs)
        if not df.empty:
            summary = []
            for tf in ['1min', '5min', '15min', 'EOD']:
                col = f'{tf}_pnl' if tf != 'EOD' else 'EOD_pnl'
                time_col = f'{tf}_time' if tf != 'EOD' else None
                
                # Count flips (where exit time < market close 15:29)
                flips = 0
                if time_col:
                    flips = (df[time_col] < '15:29').sum()
                
                summary.append({
                    'TF': tf, 
                    'Avg%': df[col].mean(), 
                    'Worst%': df[col].min(), 
                    'Flips': flips
                })
            print(pd.DataFrame(summary).to_string(index=False))

