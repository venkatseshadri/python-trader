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

class InstitutionalEngine:
    def __init__(self, top_n=3):
        self.top_n = top_n
        self.active_positions = {} 
        self.all_trades = []

    def run_simulation(self, stock_data_dict):
        # We only iterate on the 15-minute candles for ENTRIES
        stock_names = list(stock_data_dict.keys())
        df_15m_sample = stock_data_dict[stock_names[0]]['15m']
        
        for i in range(1, len(df_15m_sample)):
            row_15m = df_15m_sample.iloc[i]
            ts = row_15m['date']
            
            # 1. CHECK EXITS (Every 15m candle close)
            to_close = []
            for name, pos in self.active_positions.items():
                df_15m = stock_data_dict[name]['15m']
                if i >= len(df_15m): continue
                r = df_15m.iloc[i]
                ltp = r['close']
                lot = LOT_SIZES.get(name, 50)
                
                pnl_pts = (ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)
                pnl_rs = pnl_pts * lot
                
                exit_hit = False
                if pos['type'] == 'LONG' and r['ema5'] < r['ema9']: exit_hit = True
                elif pos['type'] == 'SHORT' and r['ema5'] > r['ema9']: exit_hit = True
                
                if exit_hit or ts.time() >= dt_time(15, 15):
                    self.all_trades.append({
                        'Time': pos['entry_time'], 'Stock': name, 'Action': f"ENTRY ({pos['type']})",
                        'Price': pos['in'], 'PnL_Rs': '-', 'Reason': '15m_HARMONY'
                    })
                    self.all_trades.append({
                        'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_rs, 2), 'Reason': '15m_STRUCTURAL_REVERSAL' if exit_hit else 'EOD'
                    })
                    to_close.append(name)
            for name in to_close: del self.active_positions[name]

            # 2. CHECK ENTRIES (Only at 15m candle closes)
            if ts.time() > dt_time(14, 30): continue
            if len(self.active_positions) >= self.top_n: continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df_15m = stock_data_dict[name]['15m']
                if i < 1 or i >= len(df_15m): continue
                r, prev = df_15m.iloc[i], df_15m.iloc[i-1]
                
                is_long = (r['ema5'] > r['ema9']) and (r['ema20'] > r['ema50']) and (r['adx'] > 20) and (r['adx'] > prev['adx'])
                is_short = (r['ema5'] < r['ema9']) and (r['ema20'] < r['ema50']) and (r['adx'] > 20) and (r['adx'] > prev['adx'])
                
                orb = stock_data_dict[name]['orb']
                side = None
                if is_long and r['close'] > orb['h']: side = 'LONG'
                elif is_short and r['close'] < orb['l']: side = 'SHORT'
                
                if side: candidates.append({'name': name, 'side': side, 'ltp': r['close'], 'time': r['date']})

            ranked = sorted(candidates, key=lambda x: x['name'])[:self.top_n]
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {'in': c['ltp'], 'type': c['side'], 'entry_time': c['time']}

def run_institutional_study(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    target_date = pd.to_datetime(target_date_str).date()
    stock_data = {}
    
    for s in top_stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df = loader.load_data(days=30)
        df_15m = resample_data(df, 15)
        df_15m['ema5'] = talib.EMA(df_15m['close'].values.astype(float), 5)
        df_15m['ema9'] = talib.EMA(df_15m['close'].values.astype(float), 9)
        df_15m['ema20'] = talib.EMA(df_15m['close'].values.astype(float), 20)
        df_15m['ema50'] = talib.EMA(df_15m['close'].values.astype(float), 50)
        df_15m['adx'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
        
        day_15m = df_15m[df_15m['date'].dt.date == target_date].reset_index(drop=True)
        
        # ORB (still 9:15-10:00)
        df_day_1m = df[df['date'].dt.date == target_date]
        mask = (df_day_1m['date'].dt.time >= dt_time(9, 15)) & (df_day_1m['date'].dt.time <= dt_time(10, 0))
        orb = {'h': df_day_1m.loc[mask, 'high'].max(), 'l': df_day_1m.loc[mask, 'low'].min()}
        
        stock_data[s] = {'15m': day_15m, 'orb': orb}

    engine = InstitutionalEngine()
    engine.run_simulation(stock_data)
    df_res = pd.DataFrame(engine.all_trades)
    
    html_file = f"python-trader/backtest_lab/reports/institutional_15m_report_{target_date_str}.html"
    total_pnl = pd.to_numeric(df_res['PnL_Rs'], errors='coerce').sum() if not df_res.empty else 0
    
    with open(html_file, "w") as f:
        f.write(f"<html><body class='p-5 font-sans'><h1>🏛️ Institutional Sniper Report (15m Candles)</h1>")
        f.write(f"<h2>Total PnL: Rs {total_pnl:,.2f} | 15m Entry & 15m Exit ACTIVE</h2>")
        if not df_res.empty: f.write(df_res.to_html(classes='table table-striped'))
        else: f.write("<h3>No institutional-grade setups found today.</h3>")
        f.write("</body></html>")
    print(f"✅ Institutional Report generated: {html_file}")

if __name__ == "__main__":
    run_institutional_study("2026-01-21")
