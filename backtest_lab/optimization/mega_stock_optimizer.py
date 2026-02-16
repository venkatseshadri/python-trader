import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time
import itertools

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.core.engine import BacktestEngine
from orbiter.filters.entry.f4_supertrend import calculate_st_values

class MegaEngine(BacktestEngine):
    """Accurate loop-based engine for path-dependent exits (TSL/SL)"""
    def __init__(self, loader, config=None):
        super().__init__(loader, config)
        self.results = []

    def run_multi_stock(self, stock_files, days=120):
        all_stats = []
        for stock_file in stock_files:
            stock_name = os.path.basename(stock_file).replace('_minute.csv', '')
            print(f"📦 Processing {stock_name}...")
            loader = DataLoader(stock_file)
            try:
                df = loader.load_data(days=days)
            except: continue
            
            dates = sorted(df['date'].dt.date.unique())
            
            # Pre-calc Indicators for speed
            closes = df['close'].values.astype(float)
            highs = df['high'].values.astype(float)
            lows = df['low'].values.astype(float)
            
            df['ema5'] = talib.EMA(closes, 5)
            df['ema9'] = talib.EMA(closes, 9)
            df['st'] = calculate_st_values(highs, lows, closes, 10, 3.0)
            df['atr'] = talib.ATR(highs, lows, closes, 14)
            df['adx'] = talib.ADX(highs, lows, closes, 14)
            
            # Group by day for the runner
            day_groups = [group for _, group in df.groupby(df['date'].dt.date)]
            
            # We will run the same engine instance over all days for this stock
            self.reset()
            for df_day in day_groups:
                self.run_day_fast(df_day)
                self.finalize_day(df_day['date'].iloc[0].date())
            
            pnl = sum(t['pnl'] for t in self.trades)
            win_rate = (sum(1 for t in self.trades if t['pnl'] > 0) / len(self.trades) * 100) if self.trades else 0
            all_stats.append({
                'Stock': stock_name, 'PnL': pnl, 'Win%': win_rate, 'Trades': len(self.trades), 'MaxDD': self.max_drawdown
            })
        
        return pd.DataFrame(all_stats)

    def run_day_fast(self, df_day):
        """Optimized version of run_day using pre-calculated indicators"""
        if df_day.empty: return
        
        # 1. ORB
        mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(9, 30))
        if mask.any():
            self.orb_high = df_day.loc[mask, 'high'].max()
            self.orb_low = df_day.loc[mask, 'low'].min()
        else:
            self.orb_high = self.orb_low = None

        closes = df_day['close'].values
        ema5 = df_day['ema5'].values
        ema9 = df_day['ema9'].values
        st = df_day['st'].values
        atr = df_day['atr'].values
        adx = df_day['adx'].values
        dates = df_day['date'].values
        
        # EMA Shifted for F5/F6 (Scope/Gap)
        # In a real run, we'd need prev day data, but here we use intra-day shifts
        e5p5 = pd.Series(ema5).shift(5).fillna(ema5[0]).values
        e9p5 = pd.Series(ema9).shift(5).fillna(ema9[0]).values
        
        atr_avg = pd.Series(atr).rolling(20).mean().fillna(atr[0]).values

        position = None
        for i in range(30, len(df_day)):
            ltp = closes[i]
            ts = pd.Timestamp(dates[i])
            
            if position:
                # Track Max Profit for TSL
                pnl_rs = self._calc_pnl_rs(position, ltp)
                position['max_pnl_rs'] = max(position.get('max_pnl_rs', 0), pnl_rs)
                
                # Exit Logic
                # 1. Hard SL
                if pnl_rs <= -(self.config['sl_pct'] / 100.0 * position['entry_spot'] * 50 * 0.5): # Approx
                     self._close(position, ltp, ts, 'HARD_SL', pnl_rs)
                # 2. TSL
                elif position['max_pnl_rs'] >= self.config['tsl_activation_rs']:
                    allowed_drop = position['max_pnl_rs'] * (self.config['tsl_retracement_pct'] / 100.0)
                    if pnl_rs <= (position['max_pnl_rs'] - allowed_drop):
                        self._close(position, ltp, ts, 'TSL_HIT', pnl_rs)
                # 3. Technical Exit
                elif (position['type'] == 'LONG' and ema5[i] < ema9[i]) or (position['type'] == 'SHORT' and ema5[i] > ema9[i]):
                    self._close(position, ltp, ts, 'TECH_REVERSAL', pnl_rs)
                
                if position['status'] == 'CLOSED':
                    self.trades.append(position)
                    position = None
                continue

            if not (self.start_t <= ts.time() <= self.end_t): continue
            
            # Scoring
            score = self._calculate_fast_score(ltp, ema5[i], ema9[i], st[i], e5p5[i], e9p5[i], atr[i], atr_avg[i], adx[i])
            
            if abs(score) >= self.config['trade_threshold']:
                position = {
                    'entry_time': ts, 'entry_spot': ltp, 
                    'type': 'LONG' if score > 0 else 'SHORT',
                    'status': 'OPEN', 'max_pnl_rs': 0, 'lot_size': 50
                }

    def _calculate_fast_score(self, ltp, e5, e9, st_val, e5p5, e9p5, atr_val, a_avg, adx_val):
        w = self.config['weights']
        
        f1 = 0
        if self.orb_high and ltp > self.orb_high: f1 = 0.25
        elif self.orb_low and ltp < self.orb_low: f1 = -0.25
        
        f2 = (ltp - e5) / ltp * 100
        f3 = (e5 - e9) / e5 * 100
        f4 = 0.20 if ltp > st_val else -0.20
        
        scope = (e5 - e5p5) / ltp * 100 * 5
        f5 = np.clip(scope, -0.20, 0.20) if abs(scope) >= 0.05 else 0
        
        exp = ((e5-e9) - (e5p5-e9p5)) / ltp * 100 * 20
        f6 = np.clip(exp, -0.20, 0.20) if abs(exp) >= 0.05 else 0
        
        rel_vol = atr_val / a_avg if a_avg > 0 else 1.0
        f7 = 0.10 if rel_vol > 1.10 else (-0.10 if rel_vol < 0.75 else 0.0)
        
        f8 = 0
        if adx_val > 25:
            if e5 > e9: f8 = 0.25
            elif e5 < e9: f8 = -0.25
            
        raw = [f1, f2, f3, f4, f5, f6, f7, f8]
        return sum(r * weight for r, weight in zip(raw, w))

def run_optimization():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "BHARTIARTL", "SBIN", "LT", "AXISBANK", "KOTAKBANK"]
    stock_files = [os.path.join(stocks_dir, f"{s}_minute.csv") for s in top_stocks]
    
    # 1. PARAMETER GRID
    weight_archetypes = {
        "Super-Alpha (Balanced)": [0.5, 1.0, 0.5, 0.5, 0.8, 1.2, 0.7, 1.0],
        "Trend Sniper (Lean)":     [1.0, 0.0, 1.5, 1.0, 0.0, 0.0, 0.0, 2.0],
        "Momentum Rocket":         [0.5, 0.5, 1.0, 0.5, 2.0, 2.0, 1.0, 1.0]
    }
    
    sl_vals = [10, 15]
    tsl_retracement_vals = [30, 50]
    thresholds = [0.35, 0.55]
    
    combinations = list(itertools.product(weight_archetypes.keys(), sl_vals, tsl_retracement_vals, thresholds))
    
    print(f"🧪 Starting Mega Optimization: {len(combinations)} parameter sets across {len(top_stocks)} stocks...")
    
    master_results = []
    
    for arch_name, sl, tsl_r, thr in combinations:
        weights = weight_archetypes[arch_name]
        print(f"\n▶️ Testing Config: {arch_name} | SL: {sl}% | TSL-R: {tsl_r}% | Thr: {thr}")
        
        engine = MegaEngine(None, config={
            'weights': weights, 'trade_threshold': thr, 
            'sl_pct': sl, 'tsl_retracement_pct': tsl_r,
            'tsl_activation_rs': 1000
        })
        
        summary_df = engine.run_multi_stock(stock_files, days=90) # 90 days for speed
        
        avg_roi = summary_df['PnL'].sum() * 50 / (100000 * len(top_stocks)) * 100
        avg_wr = summary_df['Win%'].mean()
        total_trades = summary_df['Trades'].sum()
        max_dd = summary_df['MaxDD'].max()
        
        master_results.append({
            'Config': arch_name, 'SL': sl, 'TSL-R': tsl_r, 'Thr': thr,
            'Avg ROI%': avg_roi, 'Avg Win%': avg_wr, 'Total Trades': total_trades, 'Max DD': max_dd
        })

    master_df = pd.DataFrame(master_results).sort_values('Avg ROI%', ascending=False)
    print("\n" + "="*90)
    print("🏆 MEGA OPTIMIZATION SUMMARY (TOP PERFORMING CONFIGS)")
    print("="*90)
    print(master_df.head(10).to_string(index=False))
    
    # Save the full results
    master_df.to_csv("python-trader/backtest_lab/mega_optimization_results.csv", index=False)
    print(f"\n✅ Full results saved to python-trader/backtest_lab/mega_optimization_results.csv")

if __name__ == "__main__":
    run_optimization()
