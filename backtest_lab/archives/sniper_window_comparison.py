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

class SniperORBEngine(MegaEngine):
    def run_day_sniper(self, df_day, window_end):
        if df_day.empty: return
        
        # 1. ORB Window
        orb_mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= window_end)
        if orb_mask.any():
            self.orb_high = df_day.loc[orb_mask, 'high'].max()
            self.orb_low = df_day.loc[orb_mask, 'low'].min()
        else:
            self.orb_high = self.orb_low = None

        closes = df_day['close'].values
        ema5 = df_day['ema5'].values
        ema9 = df_day['ema9'].values
        adx = df_day['adx'].values
        dates = df_day['date'].values
        
        position = None
        trades_today = 0
        max_trades = 1 # One-Shot Logic
        
        for i in range(30, len(df_day)):
            ltp = closes[i]
            ts = pd.Timestamp(dates[i])
            t = ts.time()
            
            if position:
                pnl_rs = self._calc_pnl_rs(position, ltp)
                position['max_pnl_rs'] = max(position.get('max_pnl_rs', 0), pnl_rs)
                # Tech Exit Reversal
                if (position['type'] == 'LONG' and ema5[i] < ema9[i]) or (position['type'] == 'SHORT' and ema5[i] > ema9[i]):
                    self._close(position, ltp, ts, 'TECH_REVERSAL', pnl_rs)
                if position['status'] == 'CLOSED':
                    self.trades.append(position)
                    position = None
                continue

            # Only enter after window ends
            if t <= window_end or t > dt_time(14,30): continue
            if trades_today >= max_trades: continue
            
            # Sniper Logic: Breakout + ADX > 25
            is_trending = adx[i] > 25
            score = 0
            if self.orb_high is not None and self.orb_low is not None:
                if ltp > self.orb_high and is_trending: score = 0.25
                elif ltp < self.orb_low and is_trending: score = -0.25
            
            if score != 0:
                position = {'entry_time': ts, 'entry_spot': ltp, 'type': 'LONG' if score > 0 else 'SHORT', 'status': 'OPEN', 'max_pnl_rs': 0, 'lot_size': 50}
                trades_today += 1

def run_sniper_comparison():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT"]
    stock_files = [os.path.join(stocks_dir, f"{s}_minute.csv") for s in top_stocks]
    
    # 6-Way Comparison Matrix
    configs = [
        {'name': '10:00 - No ADX', 'window': dt_time(10,0), 'use_adx': False},
        {'name': '10:00 - With ADX', 'window': dt_time(10,0), 'use_adx': True},
        {'name': '10:15 - No ADX', 'window': dt_time(10,15), 'use_adx': False},
        {'name': '10:15 - With ADX', 'window': dt_time(10,15), 'use_adx': True},
        {'name': '10:30 - No ADX', 'window': dt_time(10,30), 'use_adx': False},
        {'name': '10:30 - With ADX', 'window': dt_time(10,30), 'use_adx': True}
    ]
    
    results = []
    print(f"🧪 Running Full Matrix Comparison (One-Shot | +/- ADX25)...")
    
    for conf in configs:
        print(f"▶️ Testing {conf['name']}...")
        engine = SniperORBEngine(None, config={'weights':[1,0,0,0,0,0,0,0], 'trade_threshold':0.20, 'sl_pct':10, 'tsl_retracement_pct':30, 'tsl_activation_rs':1000})
        
        total_pnl = 0
        total_trades = 0
        
        for f in stock_files:
            loader = DataLoader(f)
            df = loader.load_data(days=90)
            closes = df['close'].values.astype(float)
            highs = df['high'].values.astype(float)
            lows = df['low'].values.astype(float)
            df['ema5'] = talib.EMA(closes, 5)
            df['ema9'] = talib.EMA(closes, 9)
            df['adx'] = talib.ADX(highs, lows, closes, 14)
            
            day_groups = [g for _, group in df.groupby(df['date'].dt.date) for g in [group]]
            engine.reset()
            for df_day in day_groups:
                # Modified runner to respect 'use_adx'
                def run_custom(self, df_day, win_end, use_adx):
                    if df_day.empty: return
                    orb_mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= win_end)
                    if orb_mask.any():
                        self.orb_high = df_day.loc[orb_mask, 'high'].max()
                        self.orb_low = df_day.loc[orb_mask, 'low'].min()
                    else: self.orb_high = self.orb_low = None

                    closes = df_day['close'].values
                    ema5 = df_day['ema5'].values
                    ema9 = df_day['ema9'].values
                    adx = df_day['adx'].values
                    dates = df_day['date'].values
                    position = None
                    trades_today = 0
                    for i in range(30, len(df_day)):
                        ltp = closes[i]
                        ts = pd.Timestamp(dates[i])
                        if position:
                            pnl_rs = self._calc_pnl_rs(position, ltp)
                            if (position['type'] == 'LONG' and ema5[i] < ema9[i]) or (position['type'] == 'SHORT' and ema5[i] > ema9[i]):
                                self._close(position, ltp, ts, 'TECH_REVERSAL', pnl_rs)
                            if position['status'] == 'CLOSED':
                                self.trades.append(position)
                                position = None
                            continue
                        if ts.time() <= win_end or ts.time() > dt_time(14,30) or trades_today >= 1: continue
                        
                        score = 0
                        is_trending = adx[i] > 25 if use_adx else True
                        if self.orb_high and ltp > self.orb_high and is_trending: score = 0.25
                        elif self.orb_low and ltp < self.orb_low and is_trending: score = -0.25
                        
                        if score != 0:
                            position = {'entry_time': ts, 'entry_spot': ltp, 'type': 'LONG' if score > 0 else 'SHORT', 'status': 'OPEN', 'max_pnl_rs': 0, 'lot_size': 50}
                            trades_today += 1

                import types
                engine.run_day_sniper = types.MethodType(run_custom, engine)
                for df_day in day_groups:
                    engine.run_day_sniper(df_day, conf['window'], conf['use_adx'])
                    engine.finalize_day(df_day['date'].iloc[0].date())
            
            total_pnl += sum(t['pnl'] for t in engine.trades)
            total_trades += len(engine.trades)
            
        results.append({
            'Config': conf['name'],
            'Avg ROI%': (total_pnl * 50 / (100000 * len(top_stocks))) * 100,
            'Trades': total_trades,
            'Win%': (sum(1 for t in engine.trades if t['pnl'] > 0) / len(engine.trades) * 100) if engine.trades else 0
        })

    res_df = pd.DataFrame(results).sort_values('Avg ROI%', ascending=False)
    print("\n" + "="*80)
    print("🏆 SNIPER ORB WINDOW COMPARISON")
    print("="*80)
    print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_sniper_comparison()
