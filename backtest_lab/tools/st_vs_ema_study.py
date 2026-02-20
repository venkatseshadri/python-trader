import json
import os
import pandas as pd
import talib
import numpy as np
from datetime import datetime
import multiprocessing

def calculate_st_manual(df, period=10, multiplier=3.0):
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

def calculate_ema(df, period=20):
    return talib.EMA(df['close'].values, timeperiod=period)

def run_head_to_head(file_list):
    results = []
    for file_path in file_list:
        try:
            with open(file_path, 'r') as f: data = json.load(f)
            df_1m = pd.DataFrame(data)
            df_1m['date'] = pd.to_datetime(df_1m['date'])
            df_1m.set_index('date', inplace=True)
            
            # ORB Calc
            orb = df_1m.between_time('09:15', '09:30')
            oh = orb['high'].max()
            
            # Entry
            post = df_1m.between_time('09:31', '15:30')
            ent = post[post['close'] > oh]
            if ent.empty: continue
            et, ep = ent.index[0], oh
            
            # Resample to 15m
            base_time = df_1m.index[0].replace(hour=9, minute=15, second=0)
            df_15 = df_1m.resample('15min', origin=base_time).agg({'high':'max','low':'min','close':'last'}).dropna()
            if len(df_15) < 21: continue
            
            df_15['ST'] = calculate_st_manual(df_15, period=10, multiplier=3.0)
            df_15['EMA20'] = calculate_ema(df_15, period=20)
            
            day_res = {'date': os.path.basename(file_path)}
            for mode in ['ST', 'EMA20']:
                ex_p = df_1m['close'].iloc[-1]
                for t, row in df_1m.loc[et:].iterrows():
                    idx = df_15.index[df_15.index < t]
                    if len(idx) < 1: continue
                    val = df_15.loc[idx[-1], mode]
                    if not pd.isna(val) and row['close'] < val:
                        ex_p = row['close']; break
                day_res[f'{mode}_pnl'] = (ex_p - ep) / ep * 100
            
            day_res['EOD_pnl'] = (df_1m['close'].iloc[-1] - ep) / ep * 100
            results.append(day_res)
        except: continue
    return results

def process_stock(symbol_path):
    symbol = os.path.basename(symbol_path)
    files = [os.path.join(symbol_path, f) for f in os.listdir(symbol_path) if f.endswith('.json')][-50:]
    if not files: return None
    
    results = run_head_to_head(files)
    if not results: return None
    
    df = pd.DataFrame(results)
    stats = {'Symbol': symbol}
    for mode in ['ST', 'EMA20', 'EOD']:
        col = f'{mode}_pnl' if mode != 'EOD' else 'EOD_pnl'
        stats[f'{mode}_Avg%'] = df[col].mean()
        stats[f'{mode}_Worst%'] = df[col].min()
        stats[f'{mode}_Win%'] = (df[col] > 0).sum() / len(df) * 100
    
    return stats

if __name__ == "__main__":
    base_path = "backtest_lab/data/intraday1pct/"
    symbol_folders = [os.path.join(base_path, d) for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    
    print(f"🚀 Starting MASS UNIVERSE STUDY (87 Stocks)...")
    
    # Use Pool for speed
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        all_stats = pool.map(process_stock, symbol_folders)
    
    # Filter out None and build final board
    final_results = [s for s in all_stats if s is not None]
    master_df = pd.DataFrame(final_results)
    
    # 🏆 Overall Winners
    print("\n🌍 --- MASS UNIVERSE SCOREBOARD (Averages) ---")
    summary = {
        'Metric': ['Avg PnL %', 'Win Rate %', 'Worst Draw %'],
        'ST (15m)': [master_df['ST_Avg%'].mean(), master_df['ST_Win%'].mean(), master_df['ST_Worst%'].min()],
        'EMA20 (15m)': [master_df['EMA20_Avg%'].mean(), master_df['EMA20_Win%'].mean(), master_df['EMA20_Worst%'].min()],
        'Hold to EOD': [master_df['EOD_Avg%'].mean(), master_df['EOD_Win%'].mean(), master_df['EOD_Worst%'].min()]
    }
    print(pd.DataFrame(summary).to_string(index=False))
    
    # Find Best Performer for EMA20
    best_ema_stocks = master_df.sort_values('EMA20_Avg%', ascending=False).head(10)
    print("\n💎 Top 10 Stocks for EMA20 (15m) Exit:")
    print(best_ema_stocks[['Symbol', 'EMA20_Avg%', 'EMA20_Win%']].to_string(index=False))
    
    master_df.to_csv("backtest_lab/mass_exit_study_results.csv", index=False)
    print(f"\n✅ Full results saved to backtest_lab/mass_exit_study_results.csv")
