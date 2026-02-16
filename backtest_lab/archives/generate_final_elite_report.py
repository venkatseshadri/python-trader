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

class FinalEliteEngine:
    def __init__(self, top_n=5, tsl_activation=1000, tsl_drop=30):
        self.top_n = top_n
        self.tsl_activation = tsl_activation
        self.tsl_drop = tsl_drop
        self.active_positions = {} 
        self.all_trades = []

    def run_simulation(self, stock_data_dict):
        stock_names = list(stock_data_dict.keys())
        max_len = max(len(df) for df in stock_data_dict.values())
        
        for i in range(45, max_len):
            to_close = []
            for name, pos in self.active_positions.items():
                df_1m = stock_data_dict[name]
                if i >= len(df_1m): continue
                row = df_1m.iloc[i]
                ltp, ts = row['close'], row['date']
                
                pnl_pts = (ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)
                pnl_rs = pnl_pts * LOT_SIZES.get(name, 50)
                pos['max_pnl_rs'] = max(pos.get('max_pnl_rs', 0), pnl_rs)
                
                exit_hit = False
                reason = ""
                # TSL Guard (30% drop after Rs 1000)
                if pos['max_pnl_rs'] >= self.tsl_activation:
                    if pnl_rs <= (pos['max_pnl_rs'] * (1 - self.tsl_drop/100)):
                        exit_hit, reason = True, f"TSL_GUARD (Max:{pos['max_pnl_rs']:.0f})"
                
                # 15m Momentum Exit
                if not exit_hit:
                    if (pos['type'] == 'LONG' and row['ema5_15m'] < row['ema9_15m']) or (pos['type'] == 'SHORT' and row['ema5_15m'] > row['ema9_15m']):
                        exit_hit, reason = True, "15m_MOMENTUM_REVERSAL"
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    if not exit_hit: reason = "EOD"
                    self.all_trades.append({
                        'Time': pos['entry_time'], 'Stock': name, 'Action': f"ENTRY ({pos['type']})",
                        'Price': pos['in'], 'PnL_Rs': '-', 'Reason': 'HARMONY_MTF'
                    })
                    self.all_trades.append({
                        'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_rs, 2), 'Reason': f"{reason} | PnL: Rs {pnl_rs:.0f}"
                    })
                    to_close.append(name)
            
            for name in to_close: del self.active_positions[name]

            curr_ts = stock_data_dict[stock_names[0]]['date'].iloc[i]
            if curr_ts.time() > dt_time(14,30): continue
            if len(self.active_positions) >= self.top_n: continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df = stock_data_dict[name]
                if i < 1 or i >= len(df): continue
                row, prev = df.iloc[i], df.iloc[i-1]
                ltp = row['close']
                
                # Entry: 5m Align + ADX Rising + 20/50 Align
                is_long = (row['ema5_5m'] > row['ema9_5m']) and (row['ema20_5m'] > row['ema50_5m']) and (row['adx'] > 20) and (row['adx'] > prev['adx'])
                is_short = (row['ema5_5m'] < row['ema9_5m']) and (row['ema20_5m'] < row['ema50_5m']) and (row['adx'] > 20) and (row['adx'] > prev['adx'])
                
                orb = df.attrs['orb']
                side = None
                if is_long and ltp > orb['h']: side = 'LONG'
                elif is_short and ltp < orb['l']: side = 'SHORT'
                
                if side: candidates.append({'name': name, 'side': side, 'ltp': row['close'], 'time': row['date']})

            ranked = sorted(candidates, key=lambda x: x['name'])[:self.top_n]
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {'in': c['ltp'], 'type': c['side'], 'entry_time': c['time'], 'max_pnl_rs': 0}

def generate_final_elite_report(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    target_date = pd.to_datetime(target_date_str).date()
    stock_data = {}
    
    for s in top_stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df = loader.load_data(days=20)
        df_5m, df_15m = resample_data(df, 5), resample_data(df, 15)
        df_5m['ema5_5m'], df_5m['ema9_5m'], df_5m['ema20_5m'], df_5m['ema50_5m'] = talib.EMA(df_5m['close'].values.astype(float), 5), talib.EMA(df_5m['close'].values.astype(float), 9), talib.EMA(df_5m['close'].values.astype(float), 20), talib.EMA(df_5m['close'].values.astype(float), 50)
        df_15m['ema5_15m'], df_15m['ema9_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5), talib.EMA(df_15m['close'].values.astype(float), 9)
        df['adx'] = talib.ADX(df['high'].values.astype(float), df['low'].values.astype(float), df['close'].values.astype(float), 14)
        df = df.merge(df_5m[['date', 'ema5_5m', 'ema9_5m', 'ema20_5m', 'ema50_5m']], on='date', how='left').ffill()
        df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m']], on='date', how='left').ffill()
        df_day = df[df['date'].dt.date == target_date].reset_index(drop=True)
        mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
        df_day.attrs['orb'] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
        stock_data[s] = df_day

    engine = FinalEliteEngine(top_n=5, tsl_activation=1000, tsl_drop=30)
    engine.run_simulation(stock_data)
    df_res = pd.DataFrame(engine.all_trades)
    
    # Calculate Summary
    numeric_pnl = pd.to_numeric(df_res['PnL_Rs'], errors='coerce').fillna(0)
    df_res['numeric_pnl'] = numeric_pnl
    summary = df_res.groupby('Stock').agg({'numeric_pnl': 'sum', 'Action': lambda x: sum(1 for a in x if 'ENTRY' in a)}).rename(columns={'numeric_pnl': 'Total Profit (Rs)', 'Action': 'Total Trades'})
    total_day_pnl = summary['Total Profit (Rs)'].sum()

    html_file = f"python-trader/backtest_lab/reports/final_elite_report_{target_date_str}.html"
    with open(html_file, "w") as f:
        f.write(f"<html><body class='p-5' style='font-family:sans-serif;'>")
        f.write(f"<div style='background:#1a237e; color:white; padding:30px; border-radius:15px; margin-bottom:30px; text-align:center;'>")
        f.write(f"<h1>🏆 FINAL ELITE PORTFOLIO SUMMARY</h1>")
        f.write(f"<h2>Date: {target_date_str} | Total Day PnL: Rs {total_day_pnl:,.2f}</h2></div>")
        
        f.write(f"<div style='margin-bottom:40px;'><h3>🏁 Stock Breakdown</h3>")
        f.write(summary.sort_values('Total Profit (Rs)', ascending=False).to_html(classes='table table-bordered table-striped'))
        f.write(f"</div>")
        
        f.write(f"<h3>📜 Transaction Timeline</h3>")
        f.write(df_res[['Time', 'Stock', 'Action', 'Price', 'PnL_Rs', 'Reason']].to_html(classes='table table-sm'))
        f.write("</body></html>")
    print(f"✅ FINAL ELITE Report generated: {html_file}")

if __name__ == "__main__":
    generate_final_elite_report("2026-01-21")
