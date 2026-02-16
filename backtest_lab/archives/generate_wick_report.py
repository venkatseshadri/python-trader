import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader

# LOT SIZES
LOT_SIZES = {"RELIANCE": 250, "TCS": 175, "LT": 175, "SBIN": 750, "HDFCBANK": 550, "INFY": 400, "ICICIBANK": 700, "AXISBANK": 625, "BHARTIARTL": 475, "KOTAKBANK": 400}

def resample_data(df, interval_min):
    df = df.set_index('date')
    resampled = df.resample(f'{interval_min}min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna()
    return resampled.reset_index()

class WickStrengthEngine:
    def __init__(self, top_n=5):
        self.top_n = top_n
        self.active_positions = {} 
        self.all_trades = []

    def run_simulation(self, stock_data_dict):
        stock_names = list(stock_data_dict.keys())
        max_len = max(len(df) for df in stock_data_dict.values())
        
        for i in range(45, max_len):
            to_close = []
            for name, pos in self.active_positions.items():
                df = stock_data_dict[name]
                if i >= len(df): continue
                row = df.iloc[i]
                ltp, ts = row['close'], row['date']
                lot = LOT_SIZES.get(name, 50)
                pnl_rs = ((ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)) * lot
                
                # Exit (1m vs 5m EMA9 Brake)
                e9_5m = row['ema9_5m']
                exit_hit = (pos['type'] == 'LONG' and ltp < e9_5m) or (pos['type'] == 'SHORT' and ltp > e9_5m)
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    reason = f"EMERGENCY_BRAKE" if exit_hit else "EOD"
                    self.all_trades.append({'Time': pos['entry_time'], 'Stock': name, 'Action': f"ENTRY ({pos['type']})", 'Price': pos['in'], 'PnL_Rs': '-', 'Reason': pos['logic']})
                    self.all_trades.append({'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF', 'Price': ltp, 'PnL_Rs': round(pnl_rs, 2), 'Reason': reason})
                    to_close.append(name)
            for name in to_close: del self.active_positions[name]

            curr_ts = stock_data_dict[stock_names[0]]['date'].iloc[i]
            if curr_ts.minute % 15 != 0: continue # Wait for 15m candle completion
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df = stock_data_dict[name]
                if i < 1 or i >= len(df): continue
                row = df.iloc[i]
                
                # 🕯️ WICK STRENGTH FILTER (On 15m candle)
                # Short logic: Close must be near Low
                candle_range = row['h_15m'] - row['l_15m']
                lower_wick = row['close'] - row['l_15m'] # For Short
                wick_pct = (lower_wick / candle_range * 100) if candle_range > 0 else 0
                
                is_full_potential = wick_pct < 25 # Less than 25% lower wick for Short
                
                # Institutional Harmony
                is_short = (row['ema5_15m'] < row['ema9_15m']) and (row['ema20_15m'] < row['ema50_15m'])
                is_fresh = (row['adx_15m'] > 20)
                
                orb = df.attrs['orb']
                if is_short and is_fresh and is_full_potential and row['close'] < orb['l']:
                    logic = f"Wick:{wick_pct:.1f}% | ADX:{row['adx_15m']:.1f}"
                    candidates.append({'name': name, 'side': 'SHORT', 'ltp': row['close'], 'time': curr_ts, 'logic': logic})

            ranked = sorted(candidates, key=lambda x: x['name'])[:self.top_n]
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {'in': c['ltp'], 'type': c['side'], 'entry_time': c['time'], 'logic': c['logic']}

def run_wick_study(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    target_date = pd.to_datetime(target_date_str).date()
    stock_data = {}
    for s in top_stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df = loader.load_data(days=30)
        df_15m = resample_data(df, 15)
        df_15m['ema5_15m'], df_15m['ema9_15m'], df_15m['ema20_15m'], df_15m['ema50_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5), talib.EMA(df_15m['close'].values.astype(float), 9), talib.EMA(df_15m['close'].values.astype(float), 20), talib.EMA(df_15m['close'].values.astype(float), 50)
        df_15m['adx_15m'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
        df_15m.rename(columns={'high':'h_15m', 'low':'l_15m'}, inplace=True)
        
        df_5m = resample_data(df, 5)
        df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 9)
        
        df = df.merge(df_5m[['date', 'ema9_5m']], on='date', how='left').ffill()
        df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m', 'ema20_15m', 'ema50_15m', 'adx_15m', 'h_15m', 'l_15m']], on='date', how='left').ffill()
        
        df_day = df[df['date'].dt.date == target_date].reset_index(drop=True)
        mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
        df_day.attrs['orb'] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
        stock_data[s] = df_day

    results = []
    wick_thresholds = [10, 5]
    
    for w_thr in wick_thresholds:
        print(f"▶️ Testing Wick Threshold: {w_thr}%")
        # Update engine logic internally for this loop
        class DynamicWickEngine(WickStrengthEngine):
            def __init__(self, top_n=5, w_limit=w_thr):
                super().__init__(top_n)
                self.w_limit = w_limit
            def run_simulation(self, stock_data_dict):
                # Copy of logic but using self.w_limit
                stock_names = list(stock_data_dict.keys())
                max_len = max(len(df) for df in stock_data_dict.values())
                for i in range(45, max_len):
                    to_close = []
                    for name, pos in self.active_positions.items():
                        df = stock_data_dict[name]
                        if i >= len(df): continue
                        row = df.iloc[i]
                        pnl_rs = ((row['close'] - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - row['close'])) * LOT_SIZES.get(name, 50)
                        exit_hit = (pos['type'] == 'LONG' and row['close'] < row['ema9_5m']) or (pos['type'] == 'SHORT' and row['close'] > row['ema9_5m'])
                        if exit_hit or row['date'].time() >= dt_time(15, 15):
                            self.all_trades.append({'Time': row['date'], 'Stock': name, 'Action': 'SQUARE-OFF', 'PnL_Rs': round(pnl_rs, 2), 'Reason': 'EMERGENCY_BRAKE' if exit_hit else 'EOD'})
                            to_close.append(name)
                    for name in to_close: del self.active_positions[name]
                    curr_ts = stock_data_dict[stock_names[0]]['date'].iloc[i]
                    if curr_ts.minute % 15 != 0: continue
                    candidates = []
                    for name in stock_names:
                        if name in self.active_positions: continue
                        df = stock_data_dict[name]
                        if i < 1 or i >= len(df): continue
                        row = df.iloc[i]
                        candle_range = row['h_15m'] - row['l_15m']
                        lower_wick = row['close'] - row['l_15m']
                        w_pct = (lower_wick / candle_range * 100) if candle_range > 0 else 0
                        is_short = (row['ema5_15m'] < row['ema9_15m']) and (row['ema20_15m'] < row['ema50_15m'])
                        if is_short and w_pct < self.w_limit and row['close'] < df.attrs['orb']['l']:
                            candidates.append({'name': name, 'side': 'SHORT', 'ltp': row['close'], 'time': curr_ts, 'logic': f"Wick:{w_pct:.1f}%"})
                    ranked = sorted(candidates, key=lambda x: x['name'])[:self.top_n]
                    for c in ranked:
                        if len(self.active_positions) >= self.top_n: break
                        self.active_positions[c['name']] = {'in': c['ltp'], 'type': c['side'], 'entry_time': c['time'], 'logic': c['logic']}

        engine = DynamicWickEngine()
        engine.run_simulation(stock_data)
        df_res = pd.DataFrame(engine.all_trades)
        pnl = pd.to_numeric(df_res['PnL_Rs'], errors='coerce').sum() if not df_res.empty else 0
        results.append({'Limit': f"{w_thr}%", 'PnL': pnl, 'Trades': len(df_res)})

    print("\n" + "="*60)
    print("🏆 WICK PURITY SENSITIVITY (Jan 21)")
    print("="*60)
    print(pd.DataFrame(results).to_string(index=False))

if __name__ == "__main__":
    run_wick_study("2026-01-21")
