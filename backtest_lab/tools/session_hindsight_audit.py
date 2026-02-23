import pandas as pd
import numpy as np
import talib
import os
from datetime import datetime, timedelta

def audit_today_session(data_dir):
    print(f"🕵️ Hindsight Audit: 17:00 - 21:00 IST Today")
    
    # 17:00 IST is 11:30 UTC. 21:00 IST is 15:30 UTC.
    
    def scan_pair(ticker_a, ticker_b):
        print(f"\n📊 Scanning Pair: {ticker_a} / {ticker_b}")
        file_a = [f for f in os.listdir(data_dir) if f.startswith(ticker_a) and "_1m_" in f][0]
        file_b = [f for f in os.listdir(data_dir) if f.startswith(ticker_b) and "_1m_" in f][0]
        
        df_a = pd.read_csv(os.path.join(data_dir, file_a))
        df_b = pd.read_csv(os.path.join(data_dir, file_b))
        
        for df in [df_a, df_b]:
            df['Datetime'] = pd.to_datetime(df['Datetime'])
            df.set_index('Datetime', inplace=True)
        
        today_start = df_a.index.max().normalize() + timedelta(hours=11, minutes=30)
        today_end = df_a.index.max().normalize() + timedelta(hours=15, minutes=30)
        
        a = df_a.loc[today_start:today_end]
        b = df_b.loc[today_start:today_end]
        
        combined = pd.DataFrame({'A': a['Close'], 'B': b['Close']}).ffill().dropna()
        combined['ratio'] = combined['A'] / combined['B']
        combined['mean'] = combined['ratio'].rolling(60).mean()
        combined['std'] = combined['ratio'].rolling(60).std()
        combined['zscore'] = (combined['ratio'] - combined['mean']) / combined['std']
        
        print(f"{'Time (UTC)':<20} | {'Signal Type':<20} | {'Metric':<10}")
        print("-" * 55)
        
        for i in range(1, len(combined)):
            t = combined.index[i]
            z = combined['zscore'].iloc[i]
            
            if z < -2.0:
                print(f"{str(t):<20} | 🟢 BUY {ticker_a} / SELL {ticker_b} | Z:{z:.2f}")
            elif z > 2.0:
                print(f"{str(t):<20} | 🔴 SELL {ticker_a} / BUY {ticker_b} | Z:{z:.2f}")

    # Gold vs Silver
    scan_pair("GC", "SI")
    # Copper vs Aluminum
    scan_pair("HG", "ALI")
    # Crude vs Natural Gas (Energy Pair)
    scan_pair("CL", "NG")
    
    # Solo Mean Reversion Audit for Crude
    print("\n📊 Solo Mean Reversion: CL (Crude Oil)")
    file_cl = [f for f in os.listdir(data_dir) if f.startswith("CL=F") and "_1m_" in f]
    if file_cl:
        df_cl = pd.read_csv(os.path.join(data_dir, file_cl[0]))
        df_cl['Datetime'] = pd.to_datetime(df_cl['Datetime'])
        df_cl.set_index('Datetime', inplace=True)
        # Standard BB 20, 2
        upper, middle, lower = talib.BBANDS(df_cl['Close'], timeperiod=20, nbdevup=2, nbdevdn=2)
        for i in range(len(df_cl)):
            ltp = df_cl['Close'].iloc[i]
            if ltp < lower.iloc[i]:
                print(f"{str(df_cl.index[i]):<20} | 🟢 SOLO BUY: CL | BB Lower")
            elif ltp > upper.iloc[i]:
                print(f"{str(df_cl.index[i]):<20} | 🔴 SOLO SELL: CL | BB Upper")

if __name__ == "__main__":
    audit_today_session("python/backtest_lab/data/yfinance")
