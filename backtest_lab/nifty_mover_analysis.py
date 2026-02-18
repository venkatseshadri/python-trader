import os
import pandas as pd
import numpy as np
import talib
from datetime import datetime, time as dt_time, timedelta
import sys
import argparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../orbiter')))

DATA_DIR = "backtest_lab/data/stocks/"
OUTPUT_FILE = "backtest_lab/orbiter_revamp_data.csv"

def calculate_slope(series, period=5):
    return (series - series.shift(period)) / series.shift(period) * 100

def get_wick_stats(df):
    if df.empty: return {"u": 0, "l": 0, "b": 0, "dom": False}
    tr = (df['high'] - df['low']).replace(0, 1e-9)
    u = (df['high'] - df[['open', 'close']].max(axis=1)) / tr
    l = (df[['open', 'close']].min(axis=1) - df['low']) / tr
    b = abs(df['close'] - df['open']) / tr
    dom = ((u + l) > 0.5).mean() > 0.5
    return {"u": round(u.mean(), 3), "l": round(l.mean(), 3), "b": round(b.mean(), 3), "dom": dom}

def get_weekly_info(df_all, target_date):
    start = target_date - timedelta(days=target_date.weekday())
    w_data = df_all[(df_all['date'].dt.date >= start) & (df_all['date'].dt.date <= target_date)]
    if w_data.empty: return "UNKNOWN", 0, 0
    o, c = w_data.iloc[0]['open'], w_data.iloc[-1]['close']
    color = "Green" if c > o else ("Red" if c < o else "Doji")
    return color, round(o, 2), round(c, 2)

def extract_comprehensive_features(df_all, df_day_1m, target_date, symbol, daily_return, yest_high, yest_close, yest_low, yest_color):
    # --- 0. MULTI-TF SETUP ---
    df_day = df_day_1m.set_index('date')
    df_5m = df_day.resample('5min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    df_15m = df_day.resample('15min').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    
    # --- A. STRUCTURAL TREND (DAILY 1D) ---
    df_daily = df_all.set_index('date').resample('1D').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
    c_1d = df_daily['close'].values.astype(float)
    e20, e50, e100 = talib.EMA(c_1d, 20), talib.EMA(c_1d, 50), talib.EMA(c_1d, 100)
    s20 = calculate_slope(pd.Series(e20), 5).values
    
    t_idx = df_daily.index.get_indexer([pd.Timestamp(target_date)], method='pad')[0]
    prev = t_idx - 1
    v20, v50, v100 = e20[prev], e50[prev], e100[prev]
    slope20 = s20[prev]
    
    direction = 'LONG' if daily_return > 0 else 'SHORT'
    long_trend_bull = (v20 > v50 > v100)
    trend_aligned = (direction == 'LONG' and v50 > v100) or (direction == 'SHORT' and v50 < v100)

    # --- B. DAILY & OPENING (1M) ---
    d_open, d_close = df_day.iloc[0]['open'], df_day.iloc[-1]['close']
    d_high, d_low = df_day['high'].max(), df_day['low'].min()
    gap_pct = (d_open - yest_close) / yest_close * 100
    w_color, w_open, w_curr = get_weekly_info(df_all, target_date)
    
    # NEW: YLow Flip Logic
    ltp_lt_ylow = d_close < yest_low
    high_gt_ylow = d_high > yest_low
    flip_proof = f"High:{d_high:.1f} > YLow:{yest_low:.1f} | LTP:{d_close:.1f} < YLow:{yest_low:.1f}"

    # --- C. SHORT TERM (1M) ---
    c_1m = df_day['close'].values.astype(float)
    h_1m, l_1m = df_day['high'].values.astype(float), df_day['low'].values.astype(float)
    ema5, ema9 = talib.EMA(c_1m, 5), talib.EMA(c_1m, 9)
    adx, atr = talib.ADX(h_1m, l_1m, c_1m, 14), talib.ATR(h_1m, l_1m, c_1m, 14)
    
    ema_crosses = np.count_nonzero(np.diff((ema5 > ema9).astype(int)))
    always_right = all(ema5 > ema9) if direction == 'LONG' else all(ema5 < ema9)
    ribbon_comp = (np.mean(abs(ema5 - ema9)/ema5 * 100 < 0.05) > 0.3)

    # --- D. SWING & PULLBACK (1M) ---
    peak_idx = df_day['high'].argmax() if direction == 'LONG' else df_day['low'].argmin()
    peak_val = df_day.iloc[peak_idx]['high' if direction == 'LONG' else 'low']
    peak_time = df_day.index[peak_idx]
    
    trend_move_pts = abs(peak_val - d_open)
    after_peak = df_day.loc[peak_time:]
    
    pb_happened, pb_depth_pts, retracement_pct, is_reversal = False, 0.0, 0.0, False
    trough_val = 0
    if len(after_peak) > 5:
        trough_val = after_peak['low'].min() if direction == 'LONG' else after_peak['high'].max()
        pb_depth_pts = abs(peak_val - trough_val)
        pb_happened = pb_depth_pts > (0.0015 * peak_val)
        if trend_move_pts > 0: retracement_pct = (pb_depth_pts / trend_move_pts) * 100
        is_reversal = (d_close < trough_val) if direction == 'LONG' else (d_close > trough_val)

    # --- E. MULTI-TF WICK ANALYSIS (@ Trough) ---
    trough_time = after_peak['low' if direction == 'LONG' else 'high'].idxmin() if direction == 'LONG' else after_peak['high'].idxmax()
    t5 = df_5m.index[df_5m.index.get_indexer([trough_time], method='pad')[0]]
    t15 = df_15m.index[df_15m.index.get_indexer([trough_time], method='pad')[0]]
    w1, w5, w15 = get_wick_stats(df_day.loc[trough_time:trough_time]), get_wick_stats(df_5m.loc[t5:t5]), get_wick_stats(df_15m.loc[t15:t15])

    # --- F. EXHAUSTION SIGNALS ---
    sideways_gap = False
    if abs(gap_pct) > 0.5:
        first_30 = df_day.iloc[:30]
        sideways_gap = ((first_30['high'].max() - first_30['low'].min()) / d_open * 100) < 0.25
    
    pre_peak = df_day.iloc[max(0, peak_idx-10):peak_idx]
    small_candles = (abs(pre_peak['close'] - pre_peak['open']).mean() < 0.3 * atr[peak_idx]) if peak_idx < len(atr) else False
    adx_decay = adx[-1] < adx.max() - 3
    atr_comp = atr[-1] < atr.max() * 0.7

    # --- G. TIMING BUCKETS ---
    buckets = [(dt_time(9,15), dt_time(10,30), "B1"), (dt_time(10,30), dt_time(12,0), "B2"), (dt_time(12,0), dt_time(13,30), "B3"), (dt_time(13,30), dt_time(15,30), "B4")]
    timing_stats = {}
    best_move = 0
    best_b = "B1"
    for s, e, b in buckets:
        m = (df_day.index.time >= s) & (df_day.index.time < e)
        if m.any():
            sub = df_day[m]
            move = abs(sub.iloc[-1]['close'] - sub.iloc[0]['open']) / sub.iloc[0]['open'] * 100
            w = get_wick_stats(sub)
            timing_stats[f"{b}_Move"] = round(move, 2)
            timing_stats[f"{b}_WickDom"] = w['dom']
            if move > best_move:
                best_move, best_b = move, b

    # --- FINAL AGGREGATION ---
    return {
        "Date": target_date, "Symbol": symbol, "Direction": direction, "Total_Move%": round(daily_return*100, 2),
        "Prev_Close": round(yest_close, 2), "Yest_High": round(yest_high, 2), "Yest_Low": round(yest_low, 2),
        "Yesterday_Color": yest_color,
        
        # 1. Trending (1D)
        "EMA20_1D": round(v20, 2), "EMA50_1D": round(v50, 2), "EMA100_1D": round(v100, 2),
        "Trend_Bull_Proof": f"{v20:.1f}>{v50:.1f}>{v100:.1f} is {long_trend_bull}",
        "EMA20_Slope": round(slope20, 3), "Trend_Aligned": trend_aligned,
        "Trend_Proof": f"Dir:{direction} vs (E50:{v50:.1f} {'<' if v50<v100 else '>'} E100:{v100:.1f})",
        
        # 2. Daily & Opening
        "LTP_gt_YHigh": d_close > yest_high, "Open_gt_YClose": d_open > yest_close,
        "LTP_lt_YLow": ltp_lt_ylow, "High_gt_YLow": high_gt_ylow,
        "Flip_Proof": flip_proof,
        "Gap%": round(gap_pct, 2), "Low_lt_YHigh": d_low < yest_high,
        "Weekly_Color": w_color, "Weekly_Proof": f"Open:{w_open} -> Curr:{w_curr}",
        
        # 3. Short Term (1M)
        "EMA5_gt_9_Always": always_right, "EMA_5_9_Crosses": ema_crosses,
        "Ribbon_Compressed": ribbon_comp, "Short_Term_Proof": f"CrossCount:{ema_crosses}, RibbonComp:{ribbon_comp}",
        
        # 4. Pullback & Swings
        "Swing_High": round(d_high, 2), "Swing_Low": round(d_low, 2),
        "Trend_Move_Pts": round(trend_move_pts, 2), "PB_Depth%": round(retracement_pct, 2),
        "PB_Time": peak_time.strftime("%H:%M"), "Is_Reversal": is_reversal,
        "PB_Proof": f"Peak:{peak_val:.1f}, Trough:{trough_val:.1f}. Retraced {retracement_pct:.1f}% of {trend_move_pts:.1f} pts move",
        
        # 5. Multi-TF Wicks (@ Trough)
        "Wick_1M_L": w1['l'], "Wick_5M_L": w5['l'], "Wick_15M_L": w15['l'],
        "Wick_1M_U": w1['u'], "Wick_5M_U": w5['u'], "Wick_15M_U": w15['u'],
        "Wick_Proof": f"15M_Lower_Wick: {w15['l']} (at {trough_time.strftime('%H:%M')})",
        
        # 6. Exhaustion
        "Sideways_Post_Gap": sideways_gap, "ATR_Compression": atr_comp, "ADX_Exhaustion": adx_decay,
        "PrePB_Small_Candles": small_candles, "PrePeak_Wick_U": get_wick_stats(pre_peak)['u'],
        
        # 7. Timing
        "Best_Bucket": best_b, "B1_Move%": timing_stats.get("B1_Move", 0), "B4_Move%": timing_stats.get("B4_Move", 0),
        "Timing_Proof": f"Max Move in {best_b} ({best_move:.2f}%). B1 WickDom:{timing_stats.get('B1_WickDom')}"
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', type=str, default=None)
    args = parser.parse_args()
    files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith("_minute.csv")])
    if args.symbol: files = [f for f in files if args.symbol in f]
    
    results = []
    print(f"🚀 Global Master Engine: Processing {len(files)} stocks (Lookback: 50 days)...")
    for f in files:
        symbol = f.replace("_minute.csv", "")
        try:
            df = pd.read_csv(os.path.join(DATA_DIR, f))
            df['date'] = pd.to_datetime(df['date'])
            daily = df.copy().set_index('date').resample('1D').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()
            
            # Yesterday metrics
            daily['pc'], daily['ph'], daily['pl'] = daily['close'].shift(1), daily['high'].shift(1), daily['low'].shift(1)
            daily['po'] = daily['open'].shift(1)
            daily['yest_color'] = daily.apply(lambda r: "Green" if r['pc'] > r['po'] else "Red", axis=1)
            daily['ret'] = (daily['close'] - daily['pc']) / daily['pc']
            
            movers = daily.tail(50)[abs(daily['ret']) >= 0.01]
            for date_val, row in movers.iterrows():
                df_day = df[df['date'].dt.date == date_val.date()].copy()
                if df_day.empty: continue
                feat = extract_comprehensive_features(df, df_day, date_val.date(), symbol, row['ret'], row['ph'], row['pc'], row['pl'], row['yest_color'])
                if feat: results.append(feat)
        except Exception as e: print(f"Error {symbol}: {e}")

    if results:
        pd.DataFrame(results).to_csv(OUTPUT_FILE, index=False)
        print(f"✅ Full NIFTY Universe Data saved to {OUTPUT_FILE} (Entries: {len(results)})")

if __name__ == "__main__":
    main()
