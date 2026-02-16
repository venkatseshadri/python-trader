import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.core.engine import BacktestEngine
from orbiter.filters.entry.f4_supertrend import calculate_st_values

class ADXExtendedEngine(BacktestEngine):
    def __init__(self, loader, adx_threshold=None, config=None):
        super().__init__(loader, config)
        self.adx_threshold = adx_threshold

    def run_day(self, df_day):
        if df_day.empty: return
        closes, highs, lows = df_day['close'].values.astype(float), df_day['high'].values.astype(float), df_day['low'].values.astype(float)
        
        # Calculate ORB Range
        orb_mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(9, 30))
        if orb_mask.any():
            self.orb_high = df_day.loc[orb_mask, 'high'].max()
            self.orb_low = df_day.loc[orb_mask, 'low'].min()
        else:
            self.orb_high = self.orb_low = None

        ema5 = talib.EMA(closes, timeperiod=5)
        ema9 = talib.EMA(closes, timeperiod=9)
        st = calculate_st_values(highs, lows, closes, 10, 3.0)
        atr = talib.ATR(highs, lows, closes, timeperiod=14)
        adx = talib.ADX(highs, lows, closes, timeperiod=14)
        
        position = None
        for i in range(30, len(df_day)):
            row = df_day.iloc[i]
            ltp = row['close']
            
            if position:
                self._check_exit(position, ltp, row['date'], ema5[i], ema9[i], st[i], atr[i], np.mean(atr[i-20:i]))
                if position['status'] == 'CLOSED':
                    self.trades.append(position)
                    position = None
                continue

            if not (self.start_t <= row['date'].time() <= self.end_t): continue
            
            score = self._calculate_score(row, ltp, ema5[i], ema9[i], st[i], ema5[i-6], ema9[i-6], atr[i], np.mean(atr[i-20:i]))
            
            if self.adx_threshold:
                is_trending = adx[i] > self.adx_threshold
                f8 = 0
                if is_trending:
                    if ema5[i] > ema9[i]: f8 = 0.25
                    elif ema5[i] < ema9[i]: f8 = -0.25
                score += f8
            
            if abs(score) >= self.config['trade_threshold']:
                position = {
                    'entry_time': row['date'], 'entry_spot': ltp, 
                    'type': 'LONG' if score > 0 else 'SHORT',
                    'status': 'OPEN', 'max_pnl_rs': 0, 'lot_size': 50
                }

def calc_stats(trades, daily_stats, capital=100000):
    if not trades: return 0, 0, 0, 0
    pnl = sum(t['pnl'] * 50 for t in trades)
    roi = (pnl / capital) * 100
    wins = [t['pnl'] for t in trades if t['pnl'] > 0]
    losses = [abs(t['pnl']) for t in trades if t['pnl'] < 0]
    pf = sum(wins) / sum(losses) if sum(losses) > 0 else 0
    
    equity = capital
    peak = capital
    max_dd = 0
    for day in daily_stats:
        equity += day['pnl_rs']
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100
        max_dd = max(max_dd, dd)
        
    return roi, pf, len(trades), max_dd
