import pandas as pd
import numpy as np
import os
import glob
import talib

def backtest_bb_mean_reversion(df, ticker, capital=10000, slippage=0.0002):
    """
    Standard Range Raider (Bollinger Bands 20, 2)
    """
    upper, middle, lower = talib.BBANDS(df['Close'], timeperiod=20, nbdevup=2, nbdevdn=2)
    
    signals = []
    pos = 0 # 1 for Long, -1 for Short
    entry_price = 0
    pnl = 0
    trades = 0
    wins = 0
    
    for i in range(len(df)):
        ltp = df['Close'].iloc[i]
        
        if pos == 0:
            if ltp < lower.iloc[i]: # Buy
                pos = 1
                entry_price = ltp * (1 + slippage)
                trades += 1
            elif ltp > upper.iloc[i]: # Sell
                pos = -1
                entry_price = ltp * (1 - slippage)
                trades += 1
        
        elif pos == 1: # Long
            if ltp > middle.iloc[i]: # Exit at Mean
                exit_price = ltp * (1 - slippage)
                pnl += (exit_price - entry_price) / entry_price * capital
                if exit_price > entry_price: wins += 1
                pos = 0
        
        elif pos == -1: # Short
            if ltp < middle.iloc[i]: # Exit at Mean
                exit_price = ltp * (1 + slippage)
                pnl += (entry_price - exit_price) / entry_price * capital
                if exit_price < entry_price: wins += 1
                pos = 0
                
    roi = (pnl / capital) * 100
    win_rate = (wins / trades * 100) if trades > 0 else 0
    return {"ticker": ticker, "roi": roi, "trades": trades, "win_rate": win_rate}

def backtest_ratio_arb(df_a, df_b, ticker_a, ticker_b, capital=10000, slippage=0.0002):
    """
    Ratio Arbitrage (Pairs Trading) between Gold and Silver
    """
    combined = pd.DataFrame({'A': df_a['Close'], 'B': df_b['Close']}).ffill().dropna()
    combined['ratio'] = combined['A'] / combined['B']
    combined['mean'] = combined['ratio'].rolling(window=120).mean()
    combined['std'] = combined['ratio'].rolling(window=120).std()
    combined['zscore'] = (combined['ratio'] - combined['mean']) / combined['std']
    
    pos = 0 # 1 if Long Ratio (Buy A, Sell B), -1 if Short Ratio (Sell A, Buy B)
    pnl = 0
    trades = 0
    wins = 0
    entry_val = 0
    
    for i in range(len(combined)):
        z = combined['zscore'].iloc[i]
        ratio = combined['ratio'].iloc[i]
        
        if pos == 0:
            if z < -2: # Ratio too low, Buy A Sell B
                pos = 1
                entry_val = ratio * (1 + slippage)
                trades += 1
            elif z > 2: # Ratio too high, Sell A Buy B
                pos = -1
                entry_val = ratio * (1 - slippage)
                trades += 1
        
        elif pos == 1: # Long Ratio
            if z > 0: # Mean Reversion
                exit_val = ratio * (1 - slippage)
                pnl += (exit_val - entry_val) / entry_val * capital
                if exit_val > entry_val: wins += 1
                pos = 0
                
        elif pos == -1: # Short Ratio
            if z < 0: # Mean Reversion
                exit_val = ratio * (1 + slippage)
                pnl += (entry_val - exit_val) / entry_val * capital
                if exit_val < entry_val: wins += 1
                pos = 0
                
    roi = (pnl / capital) * 100
    win_rate = (wins / trades * 100) if trades > 0 else 0
    return {"ticker": f"{ticker_a}/{ticker_b}", "roi": roi, "trades": trades, "win_rate": win_rate}

if __name__ == "__main__":
    DATA_DIR = "python/backtest_lab/data/yfinance"
    files = glob.glob(os.path.join(DATA_DIR, "*_1m_*.csv"))
    
    data = {}
    for f in files:
        t = os.path.basename(f).split('_')[0]
        df = pd.read_csv(f)
        df['Datetime'] = pd.to_datetime(df['Datetime'])
        df.set_index('Datetime', inplace=True)
        data[t] = df
        
    print(f"🚀 Comparative Analysis (Last 5 Days, 1m Data)")
    print(f"{'Strategy':<20} | {'Ticker':<10} | {'ROI %':<8} | {'Trades':<8} | {'Win%':<8}")
    print("-" * 65)
    
    # 1. BB Mean Reversion Results
    results = []
    for ticker, df in data.items():
        res = backtest_bb_mean_reversion(df, ticker)
        results.append(res)
        print(f"{'BB Mean Rev':<20} | {res['ticker']:<10} | {res['roi']:>7.2f}% | {res['trades']:>8} | {res['win_rate']:>7.1f}%")
        
    # 2. Ratio Arbitrage Results
    if 'GC' in data and 'SI' in data:
        res = backtest_ratio_arb(data['GC'], data['SI'], 'GC', 'SI')
        print(f"{'Ratio Arb':<20} | {res['ticker']:<10} | {res['roi']:>7.2f}% | {res['trades']:>8} | {res['win_rate']:>7.1f}%")
