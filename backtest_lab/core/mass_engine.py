import pandas as pd
import numpy as np
import talib
import os
import json
from datetime import time as dt_time
import sys

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../orbiter')))
from filters.entry.f4_supertrend import calculate_st_values

class MassOptimizer:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.score_matrix = None 
        self.price_series = None
        self.returns_series = None
        self.timestamps = None

    def precalculate_scores(self, days=250):
        from .loader import DataLoader
        loader = DataLoader(self.csv_path)
        df = loader.load_data(days=days)
        
        closes = df['close'].values
        highs = df['high'].values
        lows = df['low'].values
        
        # Returns for PnL
        self.returns_series = np.diff(closes, prepend=closes[0])
        
        print("⚡ Pre-calculating Score Matrix (F1-F7)...")

        # F1: ORB (9:15-9:30)
        f1 = np.zeros_like(closes)
        df['day'] = df['date'].dt.date
        for day, group in df.groupby('day'):
            orb_window = group[(group['date'].dt.time >= dt_time(9,15)) & (group['date'].dt.time <= dt_time(9,30))]
            if not orb_window.empty:
                h = orb_window['high'].max()
                l = orb_window['low'].min()
                # Apply to the whole day (after 9:30)
                mask = (group['date'].dt.time > dt_time(9,30))
                f1[group.index[mask & (group['close'] > h)]] = 0.25
                f1[group.index[mask & (group['close'] < l)]] = -0.25

        # EMA
        ema5 = talib.EMA(closes, timeperiod=5)
        f2 = (closes - ema5) / closes * 100
        ema9 = talib.EMA(closes, timeperiod=9)
        f3 = (ema5 - ema9) / ema5 * 100
        
        # ST
        st = calculate_st_values(highs, lows, closes, 10, 3.0)
        f4 = np.where(closes > st, 0.20, -0.20)
        
        # Velocity/Acceleration
        ema5_prev5 = pd.Series(ema5).shift(5).values
        scope = (ema5 - ema5_prev5) / closes * 100 * 5
        f5 = np.clip(scope, -0.20, 0.20)
        f5[np.abs(scope) < 0.05] = 0
        
        gap_now = ema5 - ema9
        gap_prev5 = ema5_prev5 - pd.Series(ema9).shift(5).values
        exp = (gap_now - gap_prev5) / closes * 100 * 20
        f6 = np.clip(exp, -0.20, 0.20)
        f6[np.abs(exp) < 0.05] = 0
        
        # ATR
        atr = talib.ATR(highs, lows, closes, timeperiod=14)
        atr_avg = pd.Series(atr).rolling(20).mean().values
        f7 = np.where((atr/atr_avg) > 1.10, 0.10, np.where((atr/atr_avg) < 0.75, -0.10, 0.0))
        
        self.score_matrix = np.nan_to_num(np.column_stack([np.zeros_like(closes), f2, f3, f4, f5, f6, f7]))
        self.price_series = closes
        self.timestamps = df['date']
        
        # Fast Window Mask
        times = np.array([t.time() for t in self.timestamps])
        self.window_mask = (times >= dt_time(10,30)) & (times <= dt_time(14,30))
        print(f"✅ Matrix Ready: {self.score_matrix.shape}")

    def run_grid_search(self, scenarios):
        print(f"🚀 Vectorized Grid Search for {len(scenarios)} scenarios...")
        results = []
        
        for s in scenarios:
            weights = np.array(s['weights'])
            
            # 1. BATCH CALCULATE SCORES
            scores = self.score_matrix.dot(weights)
            
            # 2. VECTORIZED PNL
            long_mask = (scores >= s['threshold']) & self.window_mask
            short_mask = (scores <= -s['threshold']) & self.window_mask
            
            # Minute-by-minute returns
            m_pnl = np.zeros_like(self.returns_series)
            m_pnl[long_mask] = self.returns_series[long_mask]
            m_pnl[short_mask] = -self.returns_series[short_mask]
            
            pnl_pts = np.sum(m_pnl)
            
            # Advanced Stats (Vectorized)
            pos_m = m_pnl > 0
            neg_m = m_pnl < 0
            gross_win = np.sum(m_pnl[pos_m])
            gross_loss = abs(np.sum(m_pnl[neg_m]))
            pf = round(gross_win / gross_loss, 2) if gross_loss > 0 else (1.0 if gross_win > 0 else 0.0)
            win_rate = round((np.sum(pos_m) / (np.sum(pos_m) + np.sum(neg_m)) * 100), 1) if (np.sum(pos_m) + np.sum(neg_m)) > 0 else 0
            
            # Trade count estimate
            trades = np.sum(np.diff(long_mask.astype(int)) == 1) + np.sum(np.diff(short_mask.astype(int)) == 1)
            
            results.append({
                'Scenario': s['name'],
                'ROI%': round((pnl_pts * 50 / 100000) * 100, 2),
                'PF': pf,
                'Win%': win_rate,
                'Trades': trades,
                'Config': s
            })
            
        return pd.DataFrame(results).sort_values('ROI%', ascending=False)
