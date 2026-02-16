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

class SoftHarmonyEngine:
    def __init__(self, top_n=5, threshold=0.20): # Lower threshold to find ANY signal
        self.top_n = top_n
        self.threshold = threshold
        self.active_positions = {} 
        self.all_trades = []

    def run_simulation(self, stock_data_dict):
        stock_names = list(stock_data_dict.keys())
        max_len = max(len(df) for df in stock_data_dict.values())
        
        for i in range(45, max_len):
            to_close = []
            for name, pos in self.active_positions.items():
                df_1m = stock_data_dict[name]['1m']
                if i >= len(df_1m): continue
                row = df_1m.iloc[i]
                ltp, ts = row['close'], row['date']
                pnl_pts = (ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)
                pnl_rs = pnl_pts * LOT_SIZES.get(name, 50)
                pos['max_pnl_rs'] = max(pos.get('max_pnl_rs', 0), pnl_rs)
                
                exit_hit = False
                reason = ""
                # Retracement Guard (25% drop from Rs 500)
                if pos['max_pnl_rs'] >= 500:
                    if pnl_rs <= (pos['max_pnl_rs'] * 0.75):
                        exit_hit, reason = True, "RETRACEMENT_GUARD"
                
                # 5m EMA Reversal
                if not exit_hit:
                    if (pos['type'] == 'LONG' and row['ema5_5m'] < row['ema9_5m']) or (pos['type'] == 'SHORT' and row['ema5_5m'] > row['ema9_5m']):
                        exit_hit, reason = True, "5m_EMA_EXIT"
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    if not exit_hit: reason = "EOD"
                    self.all_trades.append({
                        'Time': pos['entry_time'], 'Stock': name, 'Action': f"ENTRY ({pos['type']})",
                        'Price': pos['in'], 'PnL_Rs': '-', 'Reason': pos['logic']
                    })
                    self.all_trades.append({
                        'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_rs, 2), 'Reason': f"{reason} | MaxPnL: {pos['max_pnl_rs']:.0f}"
                    })
                    to_close.append(name)
            
            for name in to_close: del self.active_positions[name]

            curr_ts = stock_data_dict[stock_names[0]]['1m']['date'].iloc[i]
            if curr_ts.time() > dt_time(14,30): continue
            if len(self.active_positions) >= self.top_n: continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df_1m = stock_data_dict[name]['1m']
                if i < 1 or i >= len(df_1m): continue
                row = df_1m.iloc[i]
                prev = df_1m.iloc[i-1]
                
                # Minimum Requirements (Blockers)
                is_long_aligned = (row['ema5_5m'] > row['ema9_5m']) and (row['adx'] > 20) and (row['adx'] > prev['adx'])
                is_short_aligned = (row['ema5_5m'] < row['ema9_5m']) and (row['adx'] > 20) and (row['adx'] > prev['adx'])
                
                if not (is_long_aligned or is_short_aligned): continue
                
                orb = stock_data_dict[name]['orb']
                side = None
                if is_long_aligned and orb and row['close'] > orb['h']: side = 'LONG'
                elif is_short_aligned and orb and row['close'] < orb['l']: side = 'SHORT'
                
                if side:
                    score = 0.25 # Base
                    if (side=='LONG' and row['ema20_1m'] > row['ema50_1m']) or (side=='SHORT' and row['ema20_1m'] < row['ema50_1m']):
                        score += 0.20 # Bonus for 20/50 alignment
                    
                    candidates.append({'name': name, 'side': side, 'ltp': row['close'], 'time': row['date'], 'score': score})

            ranked = sorted(candidates, key=lambda x: x['score'], reverse=True)
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {'in': c['ltp'], 'type': c['side'], 'entry_time': c['time'], 'max_pnl_rs': 0, 'logic': f"Score:{c['score']:.2f}"}

def run_soft_study(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    target_date = pd.to_datetime(target_date_str).date()
    stock_data = {}
    for s in top_stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df = loader.load_data(days=20)
        df_5m = resample_data(df, 5)
        df_5m['ema5_5m'], df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 5), talib.EMA(df_5m['close'].values.astype(float), 9)
        df['ema20_1m'], df['ema50_1m'] = talib.EMA(df['close'].values.astype(float), 20), talib.EMA(df['close'].values.astype(float), 50)
        df['adx'] = talib.ADX(df['high'].values.astype(float), df['low'].values.astype(float), df['close'].values.astype(float), 14)
        df = df.merge(df_5m[['date', 'ema5_5m', 'ema9_5m']], on='date', how='left').ffill()
        df_day = df[df['date'].dt.date == target_date].reset_index(drop=True)
        mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
        orb = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()} if not df_day.empty and mask.any() else None
        stock_data[s] = {'1m': df_day, 'orb': orb}

    engine = SoftHarmonyEngine(top_n=5)
    engine.run_simulation(stock_data)
    df_res = pd.DataFrame(engine.all_trades)
    if df_res.empty:
        print("Final attempt: Still no trades. It seems Jan 21st was a highly corrective/choppy day for these stocks.")
        return
    total_pnl = pd.to_numeric(df_res['PnL_Rs'], errors='coerce').sum()
    html_file = f"python-trader/backtest_lab/reports/soft_harmony_report_{target_date_str}.html"
    with open(html_file, "w") as f:
        f.write(f"<html><body class='p-5'><h1>🛡️ Soft-Harmony Report (Flexible 20/50)</h1><h2>Total PnL: Rs {total_pnl:,.2f}</h2>")
        f.write(df_res.to_html(classes='table'))
        f.write("</body></html>")
    print(f"✅ Soft Report generated: {html_file}")

if __name__ == "__main__":
    run_soft_study("2026-01-21")
