import pandas as pd
import numpy as np
import talib
import os
from datetime import datetime, timedelta

def audit_today_session(data_dir):
    print(f"🕵️ Hindsight Audit: 17:00 - 21:00 IST Today")
    
    # Load GC and SI 1m data (most volatile pair)
    gc_file = [f for f in os.listdir(data_dir) if f.startswith("GC_F") and "_1m_" in f][0]
    si_file = [f for f in os.listdir(data_dir) if f.startswith("SI_F") and "_1m_" in f][0]
    
    gc = pd.read_csv(os.path.join(data_dir, gc_file))
    si = pd.read_csv(os.path.join(data_dir, si_file))
    
    for df in [gc, si]:
        df['Datetime'] = pd.to_datetime(df['Datetime'])
        df.set_index('Datetime', inplace=True)
    
    # Filter for today's session (Approx UTC for yfinance data)
    # 17:00 IST is 11:30 UTC. 21:00 IST is 15:30 UTC.
    today_start = gc.index.max().normalize() + timedelta(hours=11, minutes=30)
    today_end = gc.index.max().normalize() + timedelta(hours=15, minutes=30)
    
    gc = gc.loc[today_start:today_end]
    si = si.loc[today_start:today_end]
    
    combined = pd.DataFrame({'GC': gc['Close'], 'SI': si['Close']}).ffill().dropna()
    combined['ratio'] = combined['GC'] / combined['SI']
    combined['mean'] = combined['ratio'].rolling(60).mean()
    combined['std'] = combined['ratio'].rolling(60).std()
    combined['zscore'] = (combined['ratio'] - combined['mean']) / combined['std']
    
    # Exhaustion Logic (15m ADX + 1m EMA Gap)
    combined['ema5'] = talib.EMA(combined['GC'], timeperiod=5)
    combined['ema9'] = talib.EMA(combined['GC'], timeperiod=9)
    combined['gap'] = combined['ema5'] - combined['ema9']
    
    print(f"\n{'Time (UTC)':<20} | {'Signal Type':<20} | {'Metric':<10}")
    print("-" * 55)
    
    for i in range(1, len(combined)):
        t = combined.index[i]
        z = combined['zscore'].iloc[i]
        gap_now = abs(combined['gap'].iloc[i])
        gap_prev = abs(combined['gap'].iloc[i-1])
        
        # 1. Ratio Signals
        if z < -2.5:
            print(f"{str(t):<20} | 🟢 RATIO: BUY GC/SELL SI | Z:{z:.2f}")
        elif z > 2.5:
            print(f"{str(t):<20} | 🔴 RATIO: SELL GC/BUY SI | Z:{z:.2f}")
            
        # 2. Exhaustion Signals (Gap convergence after expansion)
        if gap_now < gap_prev * 0.5 and gap_prev > (combined['GC'].iloc[i] * 0.0005):
            print(f"{str(t):<20} | ⚠️ EXHAUSTION: REVERSAL | Gap Cls")

if __name__ == "__main__":
    audit_today_session("python/backtest_lab/data/yfinance")
