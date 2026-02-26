#!/usr/bin/env python3
"""
Utility to analyze sideways indicators - PREDICTIVE approach.
Uses morning data (09:15-10:00) to predict if rest of day will be sideways.
"""

import os
import json
import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = "backtest_lab/data/intraday1pct"
INDEX_NAME = "NIFTY 50"

def load_data(symbol):
    """Load all intraday data for a symbol"""
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
        except:
            pass
    return data

def analyze_predictive(df):
    """Analyze using morning data to predict afternoon behavior"""
    if df is None or len(df) < 60:  # Need at least 1 hour
        return None
    
    result = {}
    
    # Split: morning (09:15-10:00) vs rest of day
    morning = df.between_time('09:15', '10:00')
    afternoon = df.between_time('10:01', '15:30')
    
    if len(morning) < 10 or len(afternoon) < 30:
        return None
    
    # Morning indicators
    m_open = morning.iloc[0]['open']
    m_high = morning['high'].max()
    m_low = morning['low'].min()
    m_close = morning.iloc[-1]['close']
    
    # Afternoon indicators
    a_high = afternoon['high'].max()
    a_low = afternoon['low'].min()
    a_close = afternoon.iloc[-1]['close']
    
    # Full day
    day_high = df['high'].max()
    day_low = df['low'].min()
    day_close = df.iloc[-1]['close']
    
    # === MORNING INDICATORS (Predictive) ===
    # Morning range %
    result['morning_range_pct'] = ((m_high - m_low) / m_low) * 100 if m_low > 0 else 0
    
    # ORB (09:15-09:30)
    orb_15 = morning.between_time('09:15', '09:30')
    if len(orb_15) > 0:
        orb_high = orb_15['high'].max()
        orb_low = orb_15['low'].min()
        result['orb_15_range_pct'] = ((orb_high - orb_low) / orb_low) * 100 if orb_low > 0 else 0
        result['orb_broken_up'] = 1 if a_high > orb_high else 0
        result['orb_broken_down'] = 1 if a_low < orb_low else 0
        result['orb_intact'] = 1 if (a_high <= orb_high and a_low >= orb_low) else 0
    else:
        result['orb_15_range_pct'] = 0
        result['orb_broken_up'] = 0
        result['orb_broken_down'] = 0
        result['orb_intact'] = 1
    
    # Morning close position
    if m_high != m_low:
        result['morning_close_pos'] = (m_close - m_low) / (m_high - m_low)
    else:
        result['morning_close_pos'] = 0.5
    
    # === OUTCOME: Was afternoon sideways? ===
    # Afternoon range %
    result['afternoon_range_pct'] = ((a_high - a_low) / a_low) * 100 if a_low > 0 else 0
    
    # Full day range %
    result['day_range_pct'] = ((day_high - day_low) / day_low) * 100 if day_low > 0 else 0
    
    # True sideways: afternoon range < 0.75% AND didn't break morning high/low
    result['is_sideways'] = 1 if (result['afternoon_range_pct'] < 0.75 and 
                                   a_high <= m_high * 1.002 and 
                                   a_low >= m_low * 0.998) else 0
    
    return result

def run_analysis():
    print(f"Analyzing predictive indicators for {INDEX_NAME}...")
    
    data = load_data(INDEX_NAME)
    results = []
    
    for date_str, df in data.items():
        analysis = analyze_predictive(df)
        if analysis:
            analysis['date'] = date_str
            results.append(analysis)
    
    df = pd.DataFrame(results)
    print(f"\nTotal valid days: {len(df)}")
    print(f"Sideways days (afternoon quiet): {df['is_sideways'].sum()} ({df['is_sideways'].mean()*100:.1f}%)")
    
    # Test predictive indicators
    print("\n" + "="*80)
    print("PREDICTIVE INDICATORS TESTING")
    print("="*80)
    
    sideways_count = df['is_sideways'].sum()
    total = len(df)
    
    tests = [
        ('morning_range_pct', 'less', [0.25, 0.3, 0.4, 0.5, 0.6, 0.75]),
        ('orb_15_range_pct', 'less', [0.15, 0.2, 0.25, 0.3, 0.4]),
        ('orb_intact', 'equals', [1]),
    ]
    
    best = []
    for indicator, op, thresholds in tests:
        if indicator not in df.columns:
            continue
        print(f"\n{indicator}:")
        
        for thresh in thresholds:
            if op == 'less':
                pred = df[indicator] < thresh
            elif op == 'greater':
                pred = df[indicator] > thresh
            elif op == 'equals':
                pred = df[indicator] == thresh
            
            tp = (pred & (df['is_sideways'] == 1)).sum()
            fp = (pred & (df['is_sideways'] == 0)).sum()
            fn = ((~pred) & (df['is_sideways'] == 1)).sum()
            
            precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
            accuracy = ((df['is_sideways'] == 1) == pred).mean() * 100
            
            print(f"  thresh={thresh}: precision={precision:.1f}%, recall={recall:.1f}%, accuracy={accuracy:.1f}%")
            
            if precision > 0:
                best.append({'indicator': indicator, 'thresh': thresh, 'precision': precision, 'recall': recall})
    
    # Composite score
    print("\n" + "="*80)
    print("COMPOSITE SCORE")
    print("="*80)
    
    df['score'] = 0
    df.loc[df['morning_range_pct'] < 0.4, 'score'] += 1
    df.loc[df['orb_15_range_pct'] < 0.25, 'score'] += 1
    df.loc[df['orb_intact'] == 1, 'score'] += 1
    
    for score_thresh in [1, 2, 3]:
        pred = df['score'] >= score_thresh
        tp = (pred & (df['is_sideways'] == 1)).sum()
        fp = (pred & (df['is_sideways'] == 0)).sum()
        fn = ((~pred) & (df['is_sideways'] == 1)).sum()
        
        precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
        accuracy = ((df['is_sideways'] == 1) == pred).mean() * 100
        
        print(f"  score >= {score_thresh}: precision={precision:.1f}%, recall={recall:.1f}%, accuracy={accuracy:.1f}%")
    
    # Also show: what % of days are actually sideways?
    print(f"\n>>> Baseline: {sideways_count/total*100:.1f}% of days are truly sideways (afternoon quiet)")

if __name__ == "__main__":
    run_analysis()
