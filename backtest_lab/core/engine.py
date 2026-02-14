import pandas as pd
import numpy as np
import talib
from datetime import datetime, time as dt_time
import os
import sys

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../orbiter')))
from filters.entry.f4_supertrend import calculate_st_values

class BacktestEngine:
    def __init__(self, data_loader, config=None):
        self.loader = data_loader
        self.initial_capital = 100000
        self.reset()
        
        # Risk Defaults
        self.config = {
            'weights': [1.0, 1.2, 1.2, 0.6, 1.2, 1.2, 1.0],
            'trade_threshold': 0.30,
            'sl_pct': 10.0,
            'tsl_activation_rs': 1000,
            'tsl_retracement_pct': 50,
            'entry_start_time': "10:30",
            'entry_end_time': "14:30",
            'enabled_filters': [1, 2, 3, 4],
            'soft_sl_atr': False  # F7 as Exit signal
        }
        if config: self.config.update(config)
        self.start_t = datetime.strptime(self.config['entry_start_time'], "%H:%M").time()
        self.end_t = datetime.strptime(self.config['entry_end_time'], "%H:%M").time()

    def reset(self):
        self.current_capital = self.initial_capital
        self.trades = []
        self.daily_stats = []
        self.equity_curve = [{'date': None, 'equity': self.initial_capital}]
        self.peak_capital = self.initial_capital
        self.max_drawdown = 0

    def run_day(self, df_day):
        if df_day.empty: return
        closes, highs, lows = df_day['close'].values, df_day['high'].values, df_day['low'].values
        
        # 1. Calculate ORB Range (9:15 - 9:30)
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
        
        position = None
        
        for i in range(30, len(df_day)):
            row = df_day.iloc[i]
            ltp = row['close']
            
            if position:
                # Track Max Profit for TSL
                pnl_rs = self._calc_pnl_rs(position, ltp)
                position['max_pnl_rs'] = max(position.get('max_pnl_rs', 0), pnl_rs)
                
                # Check Exits
                self._check_exit(position, ltp, row['date'], ema5[i], ema9[i], st[i], atr[i], np.mean(atr[i-20:i]))
                if position['status'] == 'CLOSED':
                    self.trades.append(position)
                    position = None
                continue

            if not (self.start_t <= row['date'].time() <= self.end_t): continue
            
            score = self._calculate_score(row, ltp, ema5[i], ema9[i], st[i], ema5[i-6], ema9[i-6], atr[i], np.mean(atr[i-20:i]))
            if abs(score) >= self.config['trade_threshold']:
                position = {
                    'entry_time': row['date'], 'entry_spot': ltp, 
                    'type': 'LONG' if score > 0 else 'SHORT',
                    'status': 'OPEN', 'max_pnl_rs': 0, 'lot_size': 50
                }

    def _calc_pnl_rs(self, pos, ltp):
        pts = (ltp - pos['entry_spot']) if pos['type'] == 'LONG' else (pos['entry_spot'] - ltp)
        return pts * 0.5 * pos['lot_size'] # Synthetic Delta 0.5

    def _calculate_score(self, row, ltp, ema5, ema9, st, e5p5, e9p5, atr, atr_avg):
        w = list(self.config['weights']) # Copy weights
        
        # Respect enabled_filters: If provided, zero out weights for filters NOT in the list
        if 'enabled_filters' in self.config:
            enabled = self.config['enabled_filters']
            for i in range(len(w)):
                if (i + 1) not in enabled:
                    w[i] = 0.0

        # F1: ORB Logic
        f1 = 0
        if self.orb_high and self.orb_low:
            if ltp > self.orb_high: f1 = 0.25
            elif ltp < self.orb_low: f1 = -0.25

        # F2: EMA5 Location
        f2 = ((ltp - ema5) / ltp * 100)
        # F3: EMA Gap
        f3 = ((ema5 - ema9) / ema5 * 100)
        # F4: ST
        f4 = (0.20 if ltp > st else -0.20)
        # F5: Scope
        scope = (ema5 - e5p5) / ltp * 100 * 5
        f5 = np.clip(scope, -0.20, 0.20) if abs(scope) >= 0.05 else 0
        # F6: Gap Expansion
        exp = ((ema5-ema9) - (e5p5-e9p5)) / ltp * 100 * 20
        f6 = np.clip(exp, -0.20, 0.20) if abs(exp) >= 0.05 else 0
        # F7: ATR
        rel_vol = atr / atr_avg if atr_avg > 0 else 1.0
        f7 = (0.10 if rel_vol > 1.10 else (-0.10 if rel_vol < 0.75 else 0.0))
        
        raw_scores = [f1, f2, f3, f4, f5, f6, f7]
        
        # Weighted sum: Weight of 0.0 effectively disables the filter
        return sum(s * weight for s, weight in zip(raw_scores, w))

    def _check_exit(self, pos, ltp, time, ema5, ema9, st, atr, atr_avg):
        pnl_rs = self._calc_pnl_rs(pos, ltp)
        max_pnl = pos['max_pnl_rs']
        
        # 1. Hard SL (%)
        # We simulate 10% premium SL as roughly 25 points in Nifty
        if pnl_rs <= -1250: # (50 qty * 25 pts)
            return self._close(pos, ltp, time, 'HARD_SL', pnl_rs)

        # 2. Trailing SL (Rupee based)
        if max_pnl >= self.config['tsl_activation_rs']:
            # Retracement Logic: If profit drops by X% from peak
            allowed_drop = max_pnl * (self.config['tsl_retracement_pct'] / 100.0)
            if pnl_rs <= (max_pnl - allowed_drop):
                return self._close(pos, ltp, time, 'TSL_HIT', pnl_rs)

        # 3. Soft SL: ATR Contraction
        if self.config['soft_sl_atr'] and (atr / atr_avg) < 0.70:
            return self._close(pos, ltp, time, 'SOFT_ATR_EXIT', pnl_rs)

        # 4. Technical Reversal
        if (pos['type'] == 'LONG' and ema5 < ema9) or (pos['type'] == 'SHORT' and ema5 > ema9):
            return self._close(pos, ltp, time, 'TECH_REVERSAL', pnl_rs)

        if time.time() >= dt_time(15, 15):
            self._close(pos, ltp, time, 'EOD', pnl_rs)

    def _close(self, pos, ltp, time, reason, pnl_rs):
        pos.update({'status': 'CLOSED', 'exit_time': time, 'exit_spot': ltp, 'reason': reason, 'pnl': pnl_rs/50})

    def finalize_day(self, date):
        day_pnl_rs = sum(t['pnl'] * 50 for t in self.trades if t['exit_time'].date() == date)
        self.current_capital += day_pnl_rs
        self.peak_capital = max(self.peak_capital, self.current_capital)
        dd = (self.peak_capital - self.current_capital) / self.peak_capital * 100
        self.max_drawdown = max(self.max_drawdown, dd)
        self.daily_stats.append({'date': date, 'pnl_rs': day_pnl_rs})
        self.equity_curve.append({'date': date, 'equity': self.current_capital, 'drawdown_pct': dd})
