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

class SampleLoggerEngine(MegaEngine):
    def run_day_samples(self, df_day):
        if df_day.empty: return
        window_end = dt_time(10, 0)
        
        orb_mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= window_end)
        if orb_mask.any():
            self.orb_high = df_day.loc[orb_mask, 'high'].max()
            self.orb_low = df_day.loc[orb_mask, 'low'].min()
        else: return

        closes = df_day['close'].values.astype(float)
        ema5 = talib.EMA(closes, 5)
        ema9 = talib.EMA(closes, 9)
        adx = talib.ADX(df_day['high'].values.astype(float), df_day['low'].values.astype(float), closes, 14)
        dates = df_day['date'].values
        
        position = None
        trades_today = 0
        for i in range(30, len(df_day)):
            ltp = closes[i]
            ts = pd.Timestamp(dates[i])
            if position:
                exit_hit = (position['type'] == 'LONG' and ema5[i] < ema9[i]) or (position['type'] == 'SHORT' and ema5[i] > ema9[i])
                if exit_hit:
                    pnl = (ltp - position['entry_spot']) if position['type'] == 'LONG' else (position['entry_spot'] - ltp)
                    self.trades.append({
                        'Entry': position['entry_time'],
                        'Exit': ts,
                        'Type': position['type'],
                        'In': position['entry_spot'],
                        'Out': ltp,
                        'PnL_Rs': pnl * 50,
                        'Reason': 'EMA_REVERSAL',
                        'ADX_Entry': position['adx_at_entry'],
                        'ORB_H': self.orb_high
                    })
                    position = None
                continue

            if ts.time() <= window_end or ts.time() > dt_time(14,30) or trades_today >= 1: continue
            
            if adx[i] > 25:
                if self.orb_high and ltp > self.orb_high:
                    position = {'entry_time': ts, 'entry_spot': ltp, 'type': 'LONG', 'adx_at_entry': adx[i]}
                    trades_today += 1
                elif self.orb_low and ltp < self.orb_low:
                    position = {'entry_time': ts, 'entry_spot': ltp, 'type': 'SHORT', 'adx_at_entry': adx[i]}
                    trades_today += 1

def show_first_5():
    loader = DataLoader("python-trader/backtest_lab/data/stocks/RELIANCE_minute.csv")
    df = loader.load_data(days=30)
    engine = SampleLoggerEngine(None)
    
    day_groups = [g for _, group in df.groupby(df['date'].dt.date) for g in [group]]
    for df_day in day_groups:
        engine.run_day_samples(df_day)
        if len(engine.trades) >= 5: break
        
    res = pd.DataFrame(engine.trades).head(5)
    print("
" + "="*90)
    print("📋 FIRST 5 TRADES: RELIANCE (10:00 AM SNIPER)")
    print("="*90)
    print(res.to_string(index=False))

if __name__ == "__main__":
    show_first_5()
