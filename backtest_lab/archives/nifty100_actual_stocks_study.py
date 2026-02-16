import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.adx_one_year_study import ADXExtendedEngine, calc_stats
from orbiter.filters.entry.f4_supertrend import calculate_st_values

def run_actual_stock_study():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    target_stocks = [
        "RELIANCE_minute.csv",
        "TCS_minute.csv",
        "INFY_minute.csv",
        "HDFCBANK_minute.csv",
        "SBIN_minute.csv",
        "ICICIBANK_minute.csv"
    ]
    
    # Research Combinations:
    # 1. The-Core (F1+F3)
    # 2. RSI-Shield (F1+F3 + RSI > 50 for Longs)
    # 3. VWAP-Shield (F1+F3 + Price > VWAP for Longs)
    # 4. Super-Shield (F1+F3 + RSI + VWAP)
    
    # We need to extend the engine to handle RSI/VWAP for this study
    class AdvancedShieldEngine(ADXExtendedEngine):
        def run_day(self, df_day):
            if df_day.empty: return
            closes = df_day['close'].values.astype(float)
            highs = df_day['high'].values.astype(float)
            lows = df_day['low'].values.astype(float)
            vols = df_day['volume'].values.astype(float)
            
            # Indicators
            rsi = talib.RSI(closes, timeperiod=14)
            # Simple VWAP
            vwap = (vols * (highs + lows + closes) / 3).cumsum() / vols.cumsum()
            
            # Standard engine logic with extra shields
            ema5 = talib.EMA(closes, timeperiod=5)
            ema9 = talib.EMA(closes, timeperiod=9)
            st = calculate_st_values(highs, lows, closes, 10, 3.0)
            atr = talib.ATR(highs, lows, closes, timeperiod=14)
            
            # ORB
            orb_mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(9, 30))
            if orb_mask.any():
                self.orb_high = df_day.loc[orb_mask, 'high'].max()
                self.orb_low = df_day.loc[orb_mask, 'low'].min()
            else:
                self.orb_high = self.orb_low = None
                
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
                
                # Apply Shields
                is_long = score > 0
                is_short = score < 0
                
                if self.config.get('use_rsi'):
                    if is_long and rsi[i] < 50: score = 0
                    if is_short and rsi[i] > 50: score = 0
                
                if self.config.get('use_vwap'):
                    if is_long and ltp < vwap[i]: score = 0
                    if is_short and ltp > vwap[i]: score = 0
                
                if abs(score) >= self.config['trade_threshold']:
                    position = {'entry_time': row['date'], 'entry_spot': ltp, 'type': 'LONG' if score > 0 else 'SHORT', 'status': 'OPEN', 'max_pnl_rs': 0, 'lot_size': 50}

    study_configs = [
        ("The-Core (Baseline)", [1.0, 0.0, 1.5, 0.0, 0.0, 0.0, 0.0, 0.0], 0.35, False, False),
        ("RSI-Shield", [1.0, 0.0, 1.5, 0.0, 0.0, 0.0, 0.0, 0.0], 0.35, True, False),
        ("VWAP-Shield", [1.0, 0.0, 1.5, 0.0, 0.0, 0.0, 0.0, 0.0], 0.35, False, True),
        ("Super-Shield (RSI+VWAP)", [1.0, 0.0, 1.5, 0.0, 0.0, 0.0, 0.0, 0.0], 0.35, True, True)
    ]
    
    results = []
    
    for filename in target_stocks:
        csv_path = os.path.join(stocks_dir, filename)
        if not os.path.exists(csv_path): continue
            
        print(f"🚀 Analyzing {filename} with Advanced Shields...")
        loader = DataLoader(csv_path)
        df = loader.load_data(days=120) 
            
        dates = sorted(df['date'].dt.date.unique())
        
        for name, weights, thr, rsi_s, vwap_s in study_configs:
            engine = AdvancedShieldEngine(loader, config={'weights': weights, 'trade_threshold': thr, 'use_rsi': rsi_s, 'use_vwap': vwap_s})
            
            for d in dates:
                df_day = df[df['date'].dt.date == d].copy()
                engine.run_day(df_day)
                engine.finalize_day(d)
                
            roi, pf, count, dd = calc_stats(engine.trades, engine.daily_stats)
            results.append({'Stock': filename.replace('_minute.csv', ''), 'Stack': name, 'ROI %': roi, 'PF': pf, 'Trades': count, 'Max DD %': dd})

    res_df = pd.DataFrame(results)
    print("\n" + "="*80)
    print("ACTUAL NIFTY 100 STOCK PERFORMANCE (180 DAYS)")
    print("="*80)
    print(res_df.to_string(index=False))

if __name__ == "__main__":
    run_actual_stock_study()
