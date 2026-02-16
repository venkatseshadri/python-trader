import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time
import itertools

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.mega_stock_optimizer import MegaEngine

class FlexibleORBEngine(MegaEngine):
    def run_day_flexible(self, df_day, window_end, trade_start):
        if df_day.empty: return
        
        # 1. Flexible ORB Window (Always starts at 9:15)
        orb_mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= window_end)
        if orb_mask.any():
            self.orb_high = df_day.loc[orb_mask, 'high'].max()
            self.orb_low = df_day.loc[orb_mask, 'low'].min()
        else:
            self.orb_high = self.orb_low = None

        closes = df_day['close'].values
        ema5 = df_day['ema5'].values
        ema9 = df_day['ema9'].values
        dates = df_day['date'].values
        
        position = None
        for i in range(30, len(df_day)):
            ltp = closes[i]
            ts = pd.Timestamp(dates[i])
            t = ts.time()
            
            if position:
                pnl_rs = self._calc_pnl_rs(position, ltp)
                position['max_pnl_rs'] = max(position.get('max_pnl_rs', 0), pnl_rs)
                # Tech Exit (Mandatory for this study to see if it saves ORB)
                if (position['type'] == 'LONG' and ema5[i] < ema9[i]) or (position['type'] == 'SHORT' and ema5[i] > ema9[i]):
                    self._close(position, ltp, ts, 'TECH_REVERSAL', pnl_rs)
                if position['status'] == 'CLOSED':
                    self.trades.append(position)
                    position = None
                continue

            # Only enter after trade_start
            if not (trade_start <= t <= dt_time(14, 30)): continue
            
            # ORB Score Only
            score = 0
            if self.orb_high and ltp > self.orb_high: score = 0.25
            elif self.orb_low and ltp < self.orb_low: score = -0.25
            
            if abs(score) >= 0.20:
                position = {'entry_time': ts, 'entry_spot': ltp, 'type': 'LONG' if score > 0 else 'SHORT', 'status': 'OPEN', 'max_pnl_rs': 0, 'lot_size': 50}

def run_orb_sensitivity():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT"]
    stock_files = [os.path.join(stocks_dir, f"{s}_minute.csv") for s in top_stocks]
    
    # Sensitivity Parameters
    windows = [dt_time(9,30), dt_time(9,45), dt_time(10,0)] # 15m, 30m, 45m windows
    starts = [dt_time(9,30), dt_time(10,0), dt_time(10,30)]  # Start trading at
    
    combinations = list(itertools.product(windows, starts))
    results = []
    
    print(f"🧪 Testing ORB Sensitivity across {len(top_stocks)} stocks...")
    
    for w_end, t_start in combinations:
        # Logical check: can't trade before the window ends
        if t_start < w_end: continue
        
        print(f"▶️ Window End: {w_end} | Trading Start: {t_start}")
        engine = FlexibleORBEngine(None, config={'weights':[1,0,0,0,0,0,0,0], 'trade_threshold':0.20, 'sl_pct':10, 'tsl_retracement_pct':30, 'tsl_activation_rs':1000})
        
        # We need to pre-calc for all stocks first
        total_pnl = 0
        total_trades = 0
        
        for f in stock_files:
            loader = DataLoader(f)
            df = loader.load_data(days=60)
            closes = df['close'].values.astype(float)
            df['ema5'] = talib.EMA(closes, 5)
            df['ema9'] = talib.EMA(closes, 9)
            
            day_groups = [g for _, group in df.groupby(df['date'].dt.date) for g in [group]]
            engine.reset()
            for df_day in day_groups:
                engine.run_day_flexible(df_day, w_end, t_start)
                engine.finalize_day(df_day['date'].iloc[0].date())
            
            total_pnl += sum(t['pnl'] for t in engine.trades)
            total_trades += len(engine.trades)
            
        results.append({
            'Window': w_end.strftime("%H:%M"),
            'Start': t_start.strftime("%H:%M"),
            'Avg ROI%': (total_pnl * 50 / (100000 * len(top_stocks))) * 100,
            'Total Trades': total_trades,
            'Trades/Stock/Day': total_trades / (len(top_stocks) * 60)
        })

    res_df = pd.DataFrame(results).sort_values('Avg ROI%', ascending=False)
    print("\n" + "="*80)
    print("🏆 ORB WINDOW & START-TIME SENSITIVITY")
    print("="*80)
    print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_orb_sensitivity()
