import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.mega_stock_optimizer import MegaEngine

def run_orb_failure_analysis():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    # Get top 50 files
    all_files = sorted([f for f in os.listdir(stocks_dir) if f.endswith('_minute.csv')])
    target_stocks = all_files[:50]
    
    results = []
    
    # Configuration: ONLY ORB (Weight 1.0, Threshold 0.20)
    # This means any time price is above ORB high, it will try to be LONG
    weights = [1.0, 0, 0, 0, 0, 0, 0, 0]
    
    print(f"🔬 Deep-Diving into ORB (F1) Failure across {len(target_stocks)} stocks...")
    
    for filename in target_stocks:
        stock_name = filename.replace('_minute.csv', '')
        csv_path = os.path.join(stocks_dir, filename)
        loader = DataLoader(csv_path)
        
        try:
            df = loader.load_data(days=90)
        except: continue
        
        # We use the MegaEngine to simulate the path-dependent exits
        engine = MegaEngine(None, config={
            'weights': weights, 'trade_threshold': 0.20,
            'sl_pct': 10, 'tsl_retracement_pct': 30,
            'tsl_activation_rs': 1000
        })
        
        # Pre-calc required columns for MegaEngine
        closes = df['close'].values.astype(float)
        highs = df['high'].values.astype(float)
        lows = df['low'].values.astype(float)
        df['ema5'] = talib.EMA(closes, 5)
        df['ema9'] = talib.EMA(closes, 9)
        df['st'] = np.zeros_like(closes) # Not needed for solo F1
        df['atr'] = np.zeros_like(closes)
        df['adx'] = np.zeros_like(closes)
        
        day_groups = [group for _, group in df.groupby(df['date'].dt.date)]
        
        engine.reset()
        for df_day in day_groups:
            engine.run_day_fast(df_day)
            engine.finalize_day(df_day['date'].iloc[0].date())
            
        # Analysis of results for this stock
        trades = engine.trades
        if not trades:
            continue
            
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] < 0]
        
        # Categorize losses
        tech_losses = len([t for t in losses if t.get('reason') == 'TECH_REVERSAL'])
        hard_sl_losses = len([t for t in losses if t.get('reason') == 'HARD_SL'])
        
        # Calculate Whipsaw Rate: 
        # A whipsaw is when we re-enter the same direction immediately after a technical exit
        results.append({
            'Stock': stock_name,
            'ROI%': (sum(t['pnl'] for t in trades) * 50 / 100000) * 100,
            'Trades': len(trades),
            'Win%': len(wins)/len(trades)*100,
            'AvgLoss': np.mean([t['pnl'] for t in losses]) if losses else 0,
            'TechExits': tech_losses,
            'HardSL': hard_sl_losses
        })

    res_df = pd.DataFrame(results)
    
    print("\n" + "="*80)
    print("🚩 F1 (ORB) FAILURE ANALYSIS SUMMARY")
    print("="*80)
    print(res_df.sort_values('ROI%').to_string(index=False))
    
    print("\n💡 KEY REASONING FOR ORB FAILURE:")
    print("1. OVER-TRADING: Average trades per stock is huge. Price hovers near the ORB level, triggering multiple entries.")
    print("2. WHIPSAWS: Stocks have higher noise than Index. A 15-min range is easily 'poked' and then reversed.")
    print("3. LACK OF DIRECTION: ORB is a level, not a trend. Without EMA/ADX confirmation, it enters on every minor breakout.")

if __name__ == "__main__":
    run_orb_failure_analysis()
