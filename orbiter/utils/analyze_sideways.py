#!/usr/bin/env python3
"""
Utility to analyze sideways indicators from historical intraday data.
Tests multiple methods to determine which best tracks sideways markets.
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

DATA_DIR = "backtest_lab/data/intraday1pct"
INDEX_NAME = "NIFTY 50"

def load_data(symbol):
    """Load all intraday data for a symbol into a dict of date -> df"""
    folder = os.path.join(DATA_DIR, symbol)
    if not os.path.exists(folder):
        return {}
    
    data = {}
    for f in os.listdir(folder):
        if not f.endswith('.json'):
            continue
        date_str = f.replace(f"{symbol}_", "").replace(".json", "")
        filepath = os.path.join(folder, f)
        try:
            with open(filepath, 'r') as fp:
                candles = json.load(fp)
                if candles:
                    df = pd.DataFrame(candles)
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    data[date_str] = df
        except Exception as e:
            print(f"Error loading {f}: {e}")
    return data

def calculate_indicators(df):
    """Calculate all sideways indicators for a given day's dataframe"""
    if df is None or len(df) < 30:
        return None
    
    result = {}
    
    # === DAY STATS ===
    day_open = df.iloc[0]['open']
    day_high = df['high'].max()
    day_low = df['low'].min()
    day_close = df.iloc[-1]['close']
    
    # Day range %
    result['day_range_pct'] = ((day_high - day_low) / day_low) * 100 if day_low > 0 else 0
    
    # Open-Close range %
    result['oc_range_pct'] = ((abs(day_close - day_open)) / day_open) * 100 if day_open > 0 else 0
    
    # Close position (0 = low, 1 = high)
    if day_high != day_low:
        result['close_position'] = (day_close - day_low) / (day_high - day_low)
    else:
        result['close_position'] = 0.5
    
    # === FIRST HOUR (09:15-10:15) RANGE ===
    first_hour = df.between_time('09:15', '10:15')
    if len(first_hour) > 0:
        fh_high = first_hour['high'].max()
        fh_low = first_hour['low'].min()
        result['first_hour_range_pct'] = ((fh_high - fh_low) / fh_low) * 100 if fh_low > 0 else 0
    else:
        result['first_hour_range_pct'] = 0
    
    # === NR4 (Narrowest Range of last 4 candles - 4 min) ===
    # We'll use 15-min candles for NR4
    df_15 = df.resample('15min').agg({'high': 'max', 'low': 'min'}).dropna()
    if len(df_15) >= 4:
        ranges = (df_15['high'] - df_15['low']).values
        result['nr4_range'] = np.min(ranges[-4:])
        result['nr4_avg_range'] = np.mean(ranges[-4:])
        result['nr4_is_narrowest'] = 1 if ranges[-1] <= np.min(ranges[:-1]) else 0 if len(ranges) > 1 else 0
    else:
        result['nr4_range'] = 0
        result['nr4_avg_range'] = 0
        result['nr4_is_narrowest'] = 0
    
    # === VWAP DEVIATION ===
    # Calculate VWAP for the day
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
    vwap_latest = vwap.iloc[-1]
    result['vwap_deviation_pct'] = ((day_close - vwap_latest) / vwap_latest) * 100 if vwap_latest > 0 else 0
    result['vwap_within_band'] = 1 if abs(result['vwap_deviation_pct']) < 0.3 else 0
    
    # === ORB (Opening Range Breakout) ===
    # 09:15-09:30 range
    orb_range = df.between_time('09:15', '09:30')
    if len(orb_range) > 0:
        orb_high = orb_range['high'].max()
        orb_low = orb_range['low'].min()
        result['orb_range_pct'] = ((orb_high - orb_low) / orb_low) * 100 if orb_low > 0 else 0
        
        # Did price break out?
        result['broke_up'] = 1 if day_high > orb_high else 0
        result['broke_down'] = 1 if day_low < orb_low else 0
        result['within_orb'] = 1 if (day_high <= orb_high and day_low >= orb_low) else 0
    else:
        result['orb_range_pct'] = 0
        result['broke_up'] = 0
        result['broke_down'] = 0
        result['within_orb'] = 1
    
    # === PRICE IN BAND ===
    # Calculate 20-period Bollinger Bands on 15-min
    df_15 = df.resample('15min').agg({'close': 'last'}).dropna()
    if len(df_15) >= 20:
        sma = df_15['close'].rolling(20).mean()
        std = df_15['close'].rolling(20).std()
        upper = sma + 2 * std
        lower = sma - 2 * std
        latest_close = df_15['close'].iloc[-1]
        if upper.iloc[-1] != lower.iloc[-1]:
            result['bb_position'] = (latest_close - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])
        else:
            result['bb_position'] = 0.5
        # Within middle 50%?
        result['bb_middle'] = 1 if 0.25 <= result['bb_position'] <= 0.75 else 0
    else:
        result['bb_position'] = 0.5
        result['bb_middle'] = 0
    
    return result

def classify_day(df):
    """Classify a day as sideways or trending based on end-of-day characteristics"""
    if df is None or len(df) < 30:
        return None
    
    day_open = df.iloc[0]['open']
    day_high = df['high'].max()
    day_low = df['low'].min()
    day_close = df.iloc[-1]['close']
    
    # Day range as % of open
    day_range_pct = ((day_high - day_low) / day_open) * 100
    
    # True range (high-low)
    true_range = day_high - day_low
    
    # Close position: 0=low, 0.5=mid, 1=high
    if true_range > 0:
        close_position = (day_close - day_low) / true_range
    else:
        close_position = 0.5
    
    # Classification rules for "TRUE" sideways
    # 1. Very low range (less than 1%)
    # 2. OR closed near middle of range (0.35-0.65)
    
    is_sideways = False
    reason = ""
    
    if day_range_pct < 0.8:
        is_sideways = True
        reason = f"low_range_{day_range_pct:.2f}%"
    elif 0.8 <= day_range_pct < 1.2 and 0.35 <= close_position <= 0.65:
        is_sideways = True
        reason = f"narrow_middle_{day_range_pct:.2f}%"
    elif day_range_pct > 2.0:
        is_sideways = False
        reason = f"high_range_{day_range_pct:.2f}%"
    
    return {
        'is_sideways': is_sideways,
        'reason': reason,
        'day_range_pct': day_range_pct,
        'close_position': close_position
    }

def analyze_symbol(symbol):
    """Analyze all days for a symbol"""
    data = load_data(symbol)
    results = []
    
    for date_str, df in data.items():
        indicators = calculate_indicators(df)
        classification = classify_day(df)
        
        if indicators and classification:
            indicators['date'] = date_str
            indicators['is_sideways'] = classification['is_sideways']
            indicators['reason'] = classification['reason']
            results.append(indicators)
    
    return pd.DataFrame(results)

def test_indicator_thresholds(df):
    """Test different thresholds for each indicator"""
    print("\n" + "="*80)
    print("TESTING INDICATOR THRESHOLDS FOR SIDEWAYS DETECTION")
    print("="*80)
    
    if len(df) == 0:
        print("No data to analyze")
        return
    
    # Indicators to test and their thresholds
    tests = [
        ('day_range_pct', 'less', [0.5, 0.75, 1.0, 1.25, 1.5]),
        ('first_hour_range_pct', 'less', [0.3, 0.5, 0.75, 1.0]),
        ('vwap_deviation_pct', 'abs_less', [0.2, 0.3, 0.5, 0.75]),
        ('orb_range_pct', 'less', [0.2, 0.3, 0.5, 0.75]),
        ('nr4_is_narrowest', 'equals', [1]),
        ('within_orb', 'equals', [1]),
        ('bb_middle', 'equals', [1]),
    ]
    
    sideways_count = df['is_sideways'].sum()
    total_count = len(df)
    
    print(f"\nTotal days: {total_count}, Sideways: {sideways_count} ({sideways_count/total_count*100:.1f}%)")
    print("-"*80)
    
    best_results = []
    
    for indicator, op, thresholds in tests:
        if indicator not in df.columns:
            continue
            
        print(f"\n{indicator}:")
        
        for thresh in thresholds:
            if op == 'less':
                predicted = df[indicator] < thresh
            elif op == 'abs_less':
                predicted = df[indicator].abs() < thresh
            elif op == 'equals':
                predicted = df[indicator] == thresh
            else:
                continue
            
            # Calculate accuracy
            correct = (predicted == df['is_sideways']).sum()
            accuracy = correct / len(df) * 100
            
            # Precision (when we predict sideways, how often correct)
            true_positive = (predicted & df['is_sideways']).sum()
            predicted_sideways = predicted.sum()
            precision = (true_positive / predicted_sideways * 100) if predicted_sideways > 0 else 0
            
            # Recall (how many sideways days did we catch)
            recall = (true_positive / sideways_count * 100) if sideways_count > 0 else 0
            
            print(f"  thresh={thresh}: accuracy={accuracy:.1f}%, precision={precision:.1f}%, recall={recall:.1f}%")
            
            best_results.append({
                'indicator': indicator,
                'threshold': thresh,
                'accuracy': accuracy,
                'precision': precision,
                'recall': recall
            })
    
    # Find best indicator
    if best_results:
        best = max(best_results, key=lambda x: x['precision'])
        print(f"\n>>> BEST: {best['indicator']} with threshold {best['threshold']}")
        print(f"    Precision: {best['precision']:.1f}%, Recall: {best['recall']:.1f}%")
    
    return best_results

def test_composite_score(df):
    """Test composite sideways score"""
    print("\n" + "="*80)
    print("TESTING COMPOSITE SIDEWAYS SCORE")
    print("="*80)
    
    # Create composite score
    df = df.copy()
    
    # Score 1: Day range small
    df['score_range'] = (df['day_range_pct'] < 1.0).astype(int)
    
    # Score 2: First hour range small
    df['score_fhour'] = (df['first_hour_range_pct'] < 0.5).astype(int)
    
    # Score 3: Near VWAP
    df['score_vwap'] = (df['vwap_deviation_pct'].abs() < 0.3).astype(int)
    
    # Score 4: Within ORB
    df['score_orb'] = df['within_orb'].astype(int)
    
    # Score 5: NR4 (narrowest)
    df['score_nr4'] = df['nr4_is_narrowest'].astype(int)
    
    # Score 6: BB middle
    df['score_bb'] = df['bb_middle'].astype(int)
    
    df['total_score'] = df['score_range'] + df['score_fhour'] + df['score_vwap'] + df['score_orb'] + df['score_nr4'] + df['score_bb']
    
    print("\nScore breakdown:")
    for score_thresh in [2, 3, 4]:
        predicted = df['total_score'] >= score_thresh
        correct = (predicted == df['is_sideways']).sum()
        accuracy = correct / len(df) * 100
        
        true_positive = (predicted & df['is_sideways']).sum()
        predicted_sideways = predicted.sum()
        precision = (true_positive / predicted_sideways * 100) if predicted_sideways > 0 else 0
        recall = (true_positive / df['is_sideways'].sum() * 100) if df['is_sideways'].sum() > 0 else 0
        
        print(f"  score >= {score_thresh}: accuracy={accuracy:.1f}%, precision={precision:.1f}%, recall={recall:.1f}%")

def main():
    print(f"Analyzing {INDEX_NAME} intraday data...")
    
    df = analyze_symbol(INDEX_NAME)
    
    if len(df) == 0:
        print("No data found!")
        return
    
    print(f"\nLoaded {len(df)} days of data")
    print(f"Sideways days: {df['is_sideways'].sum()} ({df['is_sideways'].mean()*100:.1f}%)")
    
    # Show sample data
    print("\nSample indicators:")
    print(df[['date', 'day_range_pct', 'first_hour_range_pct', 'vwap_deviation_pct', 'is_sideways']].head(10).to_string())
    
    # Test individual indicators
    test_indicator_thresholds(df)
    
    # Test composite score
    test_composite_score(df)

if __name__ == "__main__":
    main()
