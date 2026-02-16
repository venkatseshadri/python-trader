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

class ExampleLoggerEngine(MegaEngine):
    def run_day_with_logs(self, df_day, stock_name):
        if df_day.empty: return
        window_end = dt_time(10, 0)
        tp_pct = 1.5
        sl_pct = 3.0
        
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
                pnl_pct = (ltp - position['entry_spot']) / position['entry_spot'] * 100
                if position['type'] == 'SHORT': pnl_pct = -pnl_pct
                
                # Check Exits
                reason = None
                if pnl_pct >= tp_pct: reason = f"TP HIT ({pnl_pct:.2f}%)"
                elif pnl_pct <= -sl_pct: reason = f"SL HIT ({pnl_pct:.2f}%)"
                elif (position['type'] == 'LONG' and ema5[i] < ema9[i]) or (position['type'] == 'SHORT' and ema5[i] > ema9[i]):
                    reason = "TECH REVERSAL (EMA 5/9)"
                elif ts.time() >= dt_time(15, 15):
                    reason = "EOD EXIT"

                if reason:
                    print(f"🔴 EXIT  | {ts} | {stock_name} | {reason} | Exit Price: {ltp:.2f} | Trade PnL: Rs {pnl_pct*50:.2f}")
                    position = None
                continue

            if ts.time() <= window_end or ts.time() > dt_time(14,30) or trades_today >= 1: continue
            
            # Entry Criteria
            if adx[i] > 25:
                side = None
                if ltp > self.orb_high: side = 'LONG'
                elif ltp < self.orb_low: side = 'SHORT'
                
                if side:
                    print(f"🟢 ENTRY | {ts} | {stock_name} | {side} | Entry Price: {ltp:.2f} | ORB High: {self.orb_high:.2f} | ADX: {adx[i]:.2f}")
                    position = {'entry_time': ts, 'entry_spot': ltp, 'type': side}
                    trades_today += 1

def show_examples():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    stocks = ["TCS", "RELIANCE"]
    
    print("🔎 EXAMINING INTRADAY TRADE EXAMPLES (10:00 AM ORB + ADX Sniper)")
    print("-" * 80)
    
    engine = ExampleLoggerEngine(None)
    
    for s in stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df = loader.load_data(days=30)
        day_groups = [g for _, group in df.groupby(df['date'].dt.date) for g in [group]]
        for df_day in day_groups[:10]: # Check first 10 days for samples
            engine.run_day_with_logs(df_day, s)

if __name__ == "__main__":
    show_examples()
