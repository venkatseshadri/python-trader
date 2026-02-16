import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, timedelta

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.adx_one_year_study import ADXExtendedEngine, calc_stats

def generate_stock_data(name, trend_type='bullish'):
    """Generates 100 days of 1-min data for a specific stock behavior."""
    np.random.seed(hash(name) % 2**32)
    minutes_per_day = 375
    days = 100
    total_mins = minutes_per_day * days
    
    if name == "RELIANCE": 
        base, vol = 2500, 1.2 # High price, moderate vol
    elif name == "HDFCBANK": 
        base, vol = 1600, 0.8 # Steady
    elif name == "TCS": 
        base, vol = 3800, 2.0 # High vol momentum
    else: 
        base, vol = 1000, 1.0
        
    prices = [base]
    for i in range(total_mins - 1):
        change = np.random.normal(0, vol)
        if trend_type == 'bullish': change += 0.005 # Slight drift
        prices.append(max(10, prices[-1] + change))
        
    df = pd.DataFrame({
        'date': [datetime(2025, 1, 1) + timedelta(minutes=i) for i in range(total_mins)],
        'open': prices, 'high': [p + 0.5 for p in prices], 
        'low': [p - 0.5 for p in prices], 'close': prices, 'volume': 1000
    })
    return df

def run_individual_stock_study():
    stocks = ["RELIANCE", "HDFCBANK", "TCS"]
    
    # 1. Super-Alpha Stack (F1-F7)
    sa_weights = [0.5, 1.0, 0.5, 0.5, 0.8, 1.2, 0.7]
    
    # 2. Lean Sniper Stack (F1, F3, F4, F8)
    # We zero out F2, F5, F6, F7
    lean_weights = [1.0, 0.0, 1.5, 1.0, 0.0, 0.0, 0.0, 1.5]
    
    results = []
    
    for stock_name in stocks:
        print(f"🔬 Testing {stock_name}...")
        df = generate_stock_data(stock_name)
        
        # We need to save it to a temp file for DataLoader (which expects a path)
        tmp_csv = f"/tmp/{stock_name}.csv"
        df.to_csv(tmp_csv, index=False)
        loader = DataLoader(tmp_csv)
        
        for name, weights, thr in [("Super-Alpha", sa_weights, 0.35), ("Lean-Sniper", lean_weights, 0.50)]:
            engine = ADXExtendedEngine(loader, adx_threshold=20 if "Sniper" in name else None,
                                      config={'weights': weights, 'trade_threshold': thr})
            
            dates = df['date'].dt.date.unique()
            for d in dates:
                df_day = df[df['date'].dt.date == d].copy()
                engine.run_day(df_day)
                engine.finalize_day(d)
                
            roi, pf, count, dd = calc_stats(engine.trades, engine.daily_stats)
            results.append({
                'Stock': stock_name, 'Strategy': name, 'ROI %': roi, 'PF': pf, 'Trades': count, 'Max DD %': dd
            })
            
    res_df = pd.DataFrame(results)
    print("\n" + "="*80)
    print("NIFTY 50 INDIVIDUAL STOCK PERFORMANCE COMPARISON")
    print("="*80)
    print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_individual_stock_study()
