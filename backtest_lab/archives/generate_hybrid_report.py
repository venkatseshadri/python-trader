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

class HybridSniperEngine:
    def __init__(self, top_n=3, tsl_activation=500, retracement_activation=1000):
        self.top_n = top_n
        self.tsl_activation = tsl_activation
        self.retracement_activation = retracement_activation
        self.active_positions = {} 
        self.all_trades = []

    def run_simulation(self, stock_data_dict):
        stock_names = list(stock_data_dict.keys())
        max_len = len(stock_data_dict[stock_names[0]]['1m'])
        
        for i in range(45, max_len):
            to_close = []
            for name, pos in self.active_positions.items():
                df_1m = stock_data_dict[name]['1m']
                if i >= len(df_1m): continue
                row = df_1m.iloc[i]
                ltp, ts = row['close'], row['date']
                lot = LOT_SIZES.get(name, 50)
                
                # PnL Tracking (1-minute resolution)
                pnl_pts = (ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)
                pnl_rs = pnl_pts * lot
                pos['max_pnl_rs'] = max(pos.get('max_pnl_rs', 0), pnl_rs)
                
                exit_hit = False
                reason = ""
                
                # 1. 1-Minute Structural TSL (If profit > 500)
                if pos['max_pnl_rs'] >= self.tsl_activation:
                    s_h, s_l = row['h2_15m'], row['l2_15m']
                    if pos['type'] == 'LONG' and ltp < s_l:
                        exit_hit, reason = True, f"1m_STRUCT_BREAK (LTP < {s_l:.1f})"
                    elif pos['type'] == 'SHORT' and ltp > s_h:
                        exit_hit, reason = True, f"1m_STRUCT_BREAK (LTP > {s_h:.1f})"
                
                # 2. 1-Minute Retracement Guard (If profit > 1000)
                if not exit_hit and pos['max_pnl_rs'] >= self.retracement_activation:
                    if pnl_rs <= (pos['max_pnl_rs'] * 0.70):
                        exit_hit, reason = True, f"1m_PROFIT_GUARD (30% Drop)"
                
                # 3. 15-Minute Structural Crossover (Checking every 1m)
                if not exit_hit:
                    e5, e9 = row['ema5_15m'], row['ema9_15m']
                    if (pos['type'] == 'LONG' and e5 < e9) or (pos['type'] == 'SHORT' and e5 > e9):
                        exit_hit, reason = True, "15m_STRUCTURAL_REVERSAL"
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    if not exit_hit: reason = "EOD"
                    self.all_trades.append({
                        'Time': pos['entry_time'], 'Stock': name, 'Action': f"ENTRY ({pos['type']})",
                        'Price': pos['in'], 'PnL_Rs': '-', 'Reason': '15m_INSTITUTIONAL_HARMONY'
                    })
                    self.all_trades.append({
                        'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_rs, 2), 'Reason': f"{reason} | MaxPnL: {pos['max_pnl_rs']:.0f}"
                    })
                    to_close.append(name)
            
            for name in to_close: del self.active_positions[name]

            # 4. ENTRY LOGIC (Only on 15-minute candle completions)
            curr_ts = stock_data_dict[stock_names[0]]['1m']['date'].iloc[i]
            if curr_ts.minute % 15 != 0: continue # Wait for 15m completion
            if curr_ts.time() > dt_time(14,30): continue
            if len(self.active_positions) >= self.top_n: continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df_1m = stock_data_dict[name]['1m']
                if i < 1 or i >= len(df_1m): continue
                row, prev = df_1m.iloc[i], df_1m.iloc[i-1]
                ts = row['date']
                
                # Alignment must be confirmed on the 15m and 5m indicators
                is_long = (row['ema5_15m'] > row['ema9_15m']) and (row['ema20_15m'] > row['ema50_15m']) and (row['adx_15m'] > 20)
                is_short = (row['ema5_15m'] < row['ema9_15m']) and (row['ema20_15m'] < row['ema50_15m']) and (row['adx_15m'] > 20)
                
                orb = stock_data_dict[name]['orb']
                side = None
                if is_long and row['close'] > orb['h']: side = 'LONG'
                elif is_short and row['close'] < orb['l']: side = 'SHORT'
                
                if side: candidates.append({'name': name, 'side': side, 'ltp': row['close'], 'time': ts})

            ranked = sorted(candidates, key=lambda x: x['name'])[:self.top_n]
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {'in': c['ltp'], 'type': c['side'], 'entry_time': c['time'], 'max_pnl_rs': 0}

def generate_hybrid_report(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    target_date = pd.to_datetime(target_date_str).date()
    stock_data = {}
    
    for s in top_stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df = loader.load_data(days=30)
        
        # Resample for 15m indicators
        df_15m = resample_data(df, 15)
        df_15m['ema5_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5)
        df_15m['ema9_15m'] = talib.EMA(df_15m['close'].values.astype(float), 9)
        df_15m['ema20_15m'] = talib.EMA(df_15m['close'].values.astype(float), 20)
        df_15m['ema50_15m'] = talib.EMA(df_15m['close'].values.astype(float), 50)
        df_15m['adx_15m'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
        df_15m['h2_15m'] = df_15m['high'].rolling(2).max().shift(1)
        df_15m['l2_15m'] = df_15m['low'].rolling(2).min().shift(1)
        
        # Map back to 1m
        df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m', 'ema20_15m', 'ema50_15m', 'adx_15m', 'h2_15m', 'l2_15m']], on='date', how='left').ffill()
        
        df_day = df[df['date'].dt.date == target_date].reset_index(drop=True)
        mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
        orb = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
        
        stock_data[s] = {'1m': df_day, 'orb': orb}

    engine = HybridSniperEngine()
    engine.run_simulation(stock_data)
    df_res = pd.DataFrame(engine.all_trades)
    total_pnl = pd.to_numeric(df_res['PnL_Rs'], errors='coerce').sum() if not df_res.empty else 0
    
    html_file = f"python-trader/backtest_lab/reports/hybrid_sniper_report_{target_date_str}.html"
    with open(html_file, "w") as f:
        f.write(f"<html><body class='p-5 font-sans'><h1>🚀 Hybrid Sniper Report (15m Entry | 1m TSL Exit)</h1>")
        f.write(f"<h2>Total PnL: Rs {total_pnl:,.2f}</h2>")
        if not df_res.empty: f.write(df_res.to_html(classes='table table-striped table-bordered'))
        else: f.write("<h3>No trades found with hybrid logic.</h3>")
        f.write("</body></html>")
    print(f"✅ Hybrid Report generated: {html_file}")

if __name__ == "__main__":
    generate_hybrid_report("2026-01-21")
