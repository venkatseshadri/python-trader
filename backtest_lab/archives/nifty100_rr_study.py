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

class RREngine(MegaEngine):
    def run_day_rr(self, df_day, window_end, tp_pct, sl_pct):
        if df_day.empty: return
        orb_mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= window_end)
        if orb_mask.any():
            self.orb_high = df_day.loc[orb_mask, 'high'].max()
            self.orb_low = df_day.loc[orb_mask, 'low'].min()
        else: self.orb_high = self.orb_low = None

        closes = df_day['close'].values.astype(float)
        ema5 = talib.EMA(closes, 5)
        ema9 = talib.EMA(closes, 9)
        adx = talib.ADX(df_day['high'].values.astype(float), df_day['low'].values.astype(float), closes, 14)
        
        position = None
        trades_today = 0
        for i in range(30, len(df_day)):
            ltp = closes[i]
            ts = pd.Timestamp(df_day['date'].iloc[i])
            
            if position:
                # Calculate PnL % based on Spot Price
                pnl_pct = (ltp - position['entry_spot']) / position['entry_spot'] * 100
                if position['type'] == 'SHORT': pnl_pct = -pnl_pct
                
                position['max_pnl_pct'] = max(position.get('max_pnl_pct', 0), pnl_pct)
                
                # EXIT LOGIC
                # 1. Take Profit
                if pnl_pct >= tp_pct:
                    self._close(position, ltp, ts, f'TP_{tp_pct}%', pnl_pct * 50) # Approx
                # 2. Stop Loss
                elif pnl_pct <= -sl_pct:
                    self._close(position, ltp, ts, f'SL_{sl_pct}%', pnl_pct * 50)
                # 3. Technical Exit (Safety)
                elif (position['type'] == 'LONG' and ema5[i] < ema9[i]) or (position['type'] == 'SHORT' and ema5[i] > ema9[i]):
                    self._close(position, ltp, ts, 'TECH_REVERSAL', pnl_pct * 50)
                
                if position['status'] == 'CLOSED':
                    # Fix PnL calculation for the summary
                    position['pnl'] = (position['exit_spot'] - position['entry_spot']) if position['type'] == 'LONG' else (position['entry_spot'] - position['exit_spot'])
                    self.trades.append(position)
                    position = None
                continue

            if ts.time() <= window_end or ts.time() > dt_time(14,30) or trades_today >= 1: continue
            
            if adx[i] > 25:
                if self.orb_high and ltp > self.orb_high:
                    position = {'entry_time': ts, 'entry_spot': ltp, 'type': 'LONG', 'status': 'OPEN', 'max_pnl_pct': 0, 'lot_size': 50}
                    trades_today += 1
                elif self.orb_low and ltp < self.orb_low:
                    position = {'entry_time': ts, 'entry_spot': ltp, 'type': 'SHORT', 'status': 'OPEN', 'max_pnl_pct': 0, 'lot_size': 50}
                    trades_today += 1

def run_rr_simulation():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"] # Top 5 for speed
    stock_files = [os.path.join(stocks_dir, f"{s}_minute.csv") for s in top_stocks]
    
    # RR Combinations (TP%, SL%)
    # 1:2, 1:1, 2:1
    rr_pairs = [(1, 2), (2, 4), (2, 1), (3, 1), (1.5, 1.5)]
    
    results = []
    print(f"🧪 Running RR Analysis (10:00 Window | One-Shot)...")
    
    for tp, sl in rr_pairs:
        print(f"▶️ Testing TP: {tp}% | SL: {sl}%")
        engine = RREngine(None)
        total_pts = 0
        
        for f in stock_files:
            loader = DataLoader(f)
            df = loader.load_data(days=90)
            day_groups = [g for _, group in df.groupby(df['date'].dt.date) for g in [group]]
            engine.reset()
            for df_day in day_groups:
                engine.run_day_rr(df_day, dt_time(10,0), tp, sl)
                engine.finalize_day(df_day['date'].iloc[0].date())
            total_pts += sum(t['pnl'] for t in engine.trades)
            
        results.append({
            'Ratio': f"{tp}:{sl}",
            'TP%': tp, 'SL%': sl,
            'Avg ROI%': (total_pts * 50 / (100000 * len(top_stocks))) * 100,
            'Win%': (sum(1 for t in engine.trades if t['pnl'] > 0) / len(engine.trades) * 100) if engine.trades else 0,
            'Trades': len(engine.trades)
        })

    res_df = pd.DataFrame(results).sort_values('Avg ROI%', ascending=False)
    print("\n" + "="*80)
    print("🏆 RISK-REWARD RATIO ANALYSIS (SPOT-BASED)")
    print("="*80)
    print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_rr_simulation()
