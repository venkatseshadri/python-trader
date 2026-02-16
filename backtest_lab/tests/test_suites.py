import argparse
import sys
import os
import pandas as pd
from datetime import time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from backtest_lab.core.loader import DataLoader
from backtest_lab.core.engine import BacktestEngine
from backtest_lab.core.optimizer import ScenarioManager
from backtest_lab.core.analytics import StrategyAnalytics

def run_suite(csv_path, day_count):
    loader = DataLoader(csv_path)
    full_df = loader.load_data()
    
    # Slice data
    dates = full_df['date'].dt.date.unique()
    target_dates = dates[-day_count:]
    df = full_df[full_df['date'].dt.date.isin(target_dates)].copy()
    
    manager = ScenarioManager(loader, df)
    
    # --- DEFINE TEST SUITE ---
    manager.run_scenario("1. Standard (10:30 AM)", {})
    manager.run_scenario("2. Early (09:30 AM)", {'entry_start_time': dt_time(9, 30)})
    manager.run_scenario("3. Late (11:30 AM)", {'entry_start_time': dt_time(11, 30)})
    manager.run_scenario("4. Momentum Only (F2,3,5,6)", {'enabled_filters': [2, 3, 5, 6]})
    manager.run_scenario("5. Core Trend (F2,4)", {'enabled_filters': [2, 4]})
    manager.run_scenario("6. High Conviction Late (0.40 Threshold)", {
        'entry_start_time': dt_time(11, 30),
        'trade_threshold': 0.40
    })

    # --- RESULTS ---
    summary = manager.get_summary()
    print("\n" + "="*50)
    print(f"🏆 TEST SUITE SUMMARY (Last {day_count} Days)")
    print("="*50)
    print(summary.to_string(index=False))
    
    # 4. Analytics on the best scenario
    best_idx = summary['Total PnL (Pts)'].idxmax()
    best_name = summary.loc[best_idx, 'Scenario']
    
    print(f"\n📅 PERFORMANCE BY DAY OF WEEK ({best_name})")
    
    # Dynamic config for analytics re-run
    best_config = {}
    if "Early" in best_name: best_config['entry_start_time'] = dt_time(9, 30)
    if "Late" in best_name: best_config['entry_start_time'] = dt_time(11, 30)
    if "0.40 Threshold" in best_name: best_config['trade_threshold'] = 0.40
    
    engine = BacktestEngine(loader, best_config)
    
    for d in target_dates:
        day_data = df[df['date'].dt.date == d].copy()
        engine.run_day(day_data)
        engine.finalize_day(d)
        
    dow_summary = StrategyAnalytics.analyze_days_of_week(engine.daily_stats)
    print(dow_summary.to_string())
    
    # 5. Yearly Breakdown (For Full Mode)
    if day_count > 500:
        print("\n📅 PERFORMANCE BY YEAR")
        df_y = pd.DataFrame(engine.daily_stats)
        df_y['year'] = pd.to_datetime(df_y['date']).dt.year
        yearly = df_y.groupby('year')['pnl_rs'].agg(['sum', 'count']).rename(
            columns={'sum': 'Profit (₹)', 'count': 'Days'}
        )
        print(yearly.to_string())

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    parser.add_argument('--mode', choices=['short', 'medium', 'long', 'full'], default='long')
    args = parser.parse_args()
    
    # 30 days, 6 months, 1 year (Default), Full Archive (Optional)
    counts = {'short': 30, 'medium': 120, 'long': 250, 'full': 3000}
    run_suite(args.csv, counts[args.mode])
