import os
import pandas as pd
import numpy as np
import talib
from datetime import datetime, time as dt_time, timedelta
import sys

# Path fix to include orbiter
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../orbiter')))
from filters.entry.f4_supertrend import calculate_st_values

DATA_DIR = "backtest_lab/data/stocks/"
OUTPUT_FILE = "backtest_lab/orbiter_revamp_data.csv"

def get_wick_stats(df):
    if df.empty: return 0, 0, 0
    high, low, open_p, close_p = df['high'], df['low'], df['open'], df['close']
    body = abs(close_p - open_p)
    total_range = (high - low).replace(0, 1e-9)
    upper_wick = (high - df[['open', 'close']].max(axis=1)) / total_range
    lower_wick = (df[['open', 'close']].min(axis=1) - low) / total_range
    body_ratio = body / total_range
    return upper_wick.mean(), lower_wick.mean(), body_ratio.mean()

def get_weekly_color(df_history, target_date):
    start_of_week = target_date - timedelta(days=target_date.weekday())
    week_data = df_history[(df_history['date'].dt.date >= start_of_week) & (df_history['date'].dt.date <= target_date)]
    if week_data.empty: return "Doji"
    o, c = week_data.iloc[0]['open'], week_data.iloc[-1]['close']
    if c > o * 1.001: return "Green"
    if c < o * 0.999: return "Red"
    return "Doji"

def extract_comprehensive_features(df_all, df_day, target_date, symbol, daily_return, yest_high, yest_close, yest_low):
    start_idx = df_day.index[0]
    lookback = 500 
    context_df = df_all.loc[max(0, start_idx-lookback):df_day.index[-1]].copy()
    
    c = context_df['close'].values.astype(float)
    h = context_df['high'].values.astype(float)
    l = context_df['low'].values.astype(float)
    
    # --- INDICATORS ---
    ema5, ema9 = talib.EMA(c, 5), talib.EMA(c, 9)
    ema20, ema50, ema100 = talib.EMA(c, 20), talib.EMA(c, 50), talib.EMA(c, 100)
    atr = talib.ATR(h, l, c, 14)
    adx = talib.ADX(h, l, c, 14)
    
    offset = lookback if start_idx >= lookback else start_idx
    d_ema5, d_ema9 = ema5[offset:], ema9[offset:]
    d_ema20, d_ema50, d_ema100 = ema20[offset:], ema50[offset:], ema100[offset:]
    d_atr, d_adx = atr[offset:], adx[offset:]
    
    # --- 1. TRENDING CRITERIA ---
    # Long Term (EOD snapshot)
    lt_20_50 = d_ema20[-1] > d_ema50[-1]
    lt_50_100 = d_ema50[-1] > d_ema100[-1]
    
    # Daily
    d_open, d_close = df_day.iloc[0]['open'], df_day.iloc[-1]['close']
    d_high, d_low = df_day['high'].max(), df_day['low'].min()
    gap_pct = (d_open - yest_close) / yest_close * 100
    ltp_gt_yhigh = d_close > yest_high
    open_gt_yclose = d_open > yest_close
    did_dip_yhigh = d_low < yest_high if daily_return > 0 else d_high > yest_low
    uw_day, lw_day, br_day = get_wick_stats(df_day)
    
    # Weekly
    weekly_color = get_weekly_color(df_all, target_date)
    
    # Short Term (Session analysis)
    ema_crosses = np.diff((d_ema5 > d_ema9).astype(int))
    cross_count = np.count_nonzero(ema_crosses)
    ema_always_right = all(d_ema5 > d_ema9) if daily_return > 0 else all(d_ema5 < d_ema9)
    
    # --- 2. PULLBACK & REVERSAL ---
    pb_occured = False
    pb_depth = 0
    pb_time_bucket = 0
    rev_confirmed = False
    pre_rev_ema_gap = 0
    pre_rev_adx = 0
    pre_rev_atr_ratio = 0
    
    peak_idx_relative = df_day['high'].argmax() if daily_return > 0 else df_day['low'].argmin()
    peak_idx = df_day.index[peak_idx_relative]
    after_peak = df_day.loc[peak_idx:]
    
    if len(after_peak) > 5:
        peak_val = df_day.loc[peak_idx, 'high' if daily_return > 0 else 'low']
        trough_val = after_peak['low'].min() if daily_return > 0 else after_peak['high'].max()
        pb_depth = abs(peak_val - trough_val) / peak_val * 100
        if pb_depth > 0.15:
            pb_occured = True
            pb_time = df_day.loc[after_peak['low' if daily_return > 0 else 'high'].idxmin() if daily_return > 0 else after_peak['high'].idxmax(), 'date'].time()
            pb_time_bucket = 1 if pb_time < dt_time(10,30) else (2 if pb_time < dt_time(12,0) else (3 if pb_time < dt_time(13,30) else 4))
            rev_confirmed = (d_close > trough_val) if daily_return > 0 else (d_close < trough_val)
            
            # Context BEFORE pullback/reversal starts
            pre_rev_idx = peak_idx_relative + offset
            pre_rev_ema_gap = abs(ema5[pre_rev_idx] - ema9[pre_rev_idx]) / ema5[pre_rev_idx] * 100
            pre_rev_adx = adx[pre_rev_idx]
            pre_rev_atr_ratio = atr[pre_rev_idx] / np.mean(atr[max(0, pre_rev_idx-20):pre_rev_idx])

    # --- 3. EXHAUSTION ---
    sideways_post_gap = False
    if abs(gap_pct) > 0.5:
        post_gap_window = df_day.iloc[:30] # first 30 mins
        if (post_gap_window['high'].max() - post_gap_window['low'].min()) / d_open * 100 < 0.25:
            sideways_post_gap = True
            
    # Small candles + wicks before peak
    pre_peak_window = df_day.iloc[max(0, peak_idx_relative-10):peak_idx_relative]
    uw_pre, lw_pre, br_pre = get_wick_stats(pre_peak_window)
    pre_peak_compression = br_pre < 0.4 # Body is less than 40% of range
    
    adx_peak = d_adx.max()
    adx_ends_lower = d_adx[-1] < adx_peak - 3
    atr_peak = d_atr.max()
    atr_ends_lower = d_atr[-1] < 0.7 * atr_peak

    # --- 4. TIMING & BUCKETS ---
    buckets = [(dt_time(9,15), dt_time(10,30)), (dt_time(10,30), dt_time(12,0)), (dt_time(12,0), dt_time(13,30)), (dt_time(13,30), dt_time(15,30))]
    b_data = []
    for start, end in buckets:
        m = (df_day['date'].dt.time >= start) & (df_day['date'].dt.time < end)
        if m.any():
            subset = df_day[m]
            move = abs(subset.iloc[-1]['close'] - subset.iloc[0]['open']) / subset.iloc[0]['open'] * 100
            uw, lw, br = get_wick_stats(subset)
            # Exhaustion in bucket: ADX falling during bucket
            b_adx = d_adx[np.where(m)[0]]
            b_exhaustion = b_adx[-1] < b_adx.max() - 2 if len(b_adx) > 0 else False
            b_data.append({'move': move, 'wick': (uw+lw)/2, 'exhaustion': b_exhaustion})
        else:
            b_data.append({'move': 0, 'wick': 0, 'exhaustion': False})

    # --- SCORING VS RESTRICTIVE LOGIC (PRELIMINARY) ---
    # Restrictive: Trend must be aligned
    is_trend_aligned = (daily_return > 0 and lt_50_100) or (daily_return < 0 and not lt_50_100)
    
    return {
        'Date': target_date, 'Symbol': symbol, 'Direction': 'LONG' if daily_return > 0 else 'SHORT', 'Total_Move%': round(daily_return*100, 2),
        'Trend_20_gt_50': lt_20_50, 'Trend_50_gt_100': lt_50_100, 'Trend_Aligned': is_trend_aligned,
        'LTP_gt_YHigh': ltp_gt_yhigh, 'Open_gt_YClose': open_gt_yclose, 'Gap%': round(gap_pct, 2),
        'Did_Dip_YHigh': did_dip_yhigh, 'Day_Wick_U': round(uw_day, 3), 'Day_Wick_L': round(lw_day, 3),
        'Weekly_Color': weekly_color, 'EMA_Crosses': cross_count, 'EMA_Always_Correct': ema_always_right,
        'Pullback_Happened': pb_occured, 'Pullback_Depth%': round(pb_depth, 2), 'Pullback_Bucket': pb_time_bucket,
        'Reversal_Confirmed': rev_confirmed, 'PreRev_EMA_Gap': round(pre_rev_ema_gap, 3), 'PreRev_ADX': round(pre_rev_adx, 2),
        'PreRev_ATR_Ratio': round(pre_rev_atr_ratio, 2), 'Sideways_Post_Gap': sideways_post_gap,
        'PrePeak_Wick_U': round(uw_pre, 3), 'PrePeak_Compression': pre_peak_compression,
        'ADX_Exhaustion': adx_ends_lower, 'ATR_Compression': atr_ends_lower,
        'Best_Bucket': np.argmax([b['move'] for b in b_data]) + 1,
        'B1_Move': round(b_data[0]['move'], 2), 'B2_Move': round(b_data[1]['move'], 2), 
        'B3_Move': round(b_data[2]['move'], 2), 'B4_Move': round(b_data[3]['move'], 2),
        'B1_Exhaustion': b_data[0]['exhaustion'], 'B4_Exhaustion': b_data[3]['exhaustion']
    }

def main():
    files = [f for f in os.listdir(DATA_DIR) if f.endswith("_minute.csv")]
    results = []
    print(f"🚀 Processing {len(files[:60])} stocks for deep-dive analysis...")
    for f in files[:60]:
        symbol = f.replace("_minute.csv", "")
        try:
            df = pd.read_csv(os.path.join(DATA_DIR, f))
            df['date'] = pd.to_datetime(df['date'])
            daily = df.resample('D', on='date').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
            daily['pc'], daily['ph'], daily['pl'] = daily['close'].shift(1), daily['high'].shift(1), daily['low'].shift(1)
            daily['ret'] = (daily['close'] - daily['pc']) / daily['pc']
            # Analyze last 125 trading days (~6 months)
            movers = daily.tail(125)[abs(daily['ret']) >= 0.01]
            
            for date_val, row in movers.iterrows():
                df_day = df[df['date'].dt.date == date_val.date()].copy()
                if df_day.empty: continue
                feat = extract_comprehensive_features(df, df_day, date_val.date(), symbol, row['ret'], row['ph'], row['pc'], row['pl'])
                if feat: results.append(feat)
        except Exception as e: print(f"Error {symbol}: {e}")

    final_df = pd.DataFrame(results)
    final_df.to_csv(OUTPUT_FILE, index=False)
    
    print("\n" + "="*50)
    print("🎯 REVERSE-ENGINEERED FILTER INSIGHTS")
    print("="*50)
    print(f"Total 1% Events: {len(final_df)}")
    print(f"Restrictive Filter 'Trend_Aligned' Hit Rate: {final_df['Trend_Aligned'].mean()*100:.1f}%")
    print(f"Predictive 'Open_gt_YClose' (for Longs): {final_df[final_df['Direction']=='LONG']['Open_gt_YClose'].mean()*100:.1f}%")
    print(f"Average Exhaustion Signal at EOD: {final_df['ADX_Exhaustion'].mean()*100:.1f}%")
    print(f"Most Profitable Timing: Bucket {final_df['Best_Bucket'].mode()[0]} ({(final_df['Best_Bucket']==1).mean()*100:.1f}% of moves)")
    print("="*50)

if __name__ == "__main__":
    main()
