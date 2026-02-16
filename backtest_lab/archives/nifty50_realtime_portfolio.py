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

# LOT SIZES
LOT_SIZES = {"RELIANCE": 250, "TCS": 175, "LT": 175, "SBIN": 750, "HDFCBANK": 550, "INFY": 400, "ICICIBANK": 700, "AXISBANK": 625, "BHARTIARTL": 475, "KOTAKBANK": 400}

class RealtimePortfolioEngine:
    def __init__(self, top_n=5, threshold=0.35):
        self.top_n = top_n
        self.threshold = threshold
        self.active_positions = {} # {stock: pos_data}
        self.all_trades = []
        self.weights = [1.0, 0.0, 1.5, 1.0, 0.0, 0.0, 0.0, 1.5] # F1, F3, F4, F8 Focus

    def run_simulation(self, stock_data_dict):
        # stock_data_dict: {stock_name: df}
        all_dates = sorted(next(iter(stock_data_dict.values()))['date'].dt.date.unique())
        
        for d in all_dates:
            self.active_positions = {}
            # Extract minute-by-minute data for this day across all stocks
            day_dfs = {name: df[df['date'].dt.date == d].reset_index(drop=True) for name, df in stock_data_dict.items()}
            
            # ORB Logic for all stocks
            orb_levels = {}
            for name, df_day in day_dfs.items():
                mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
                if not df_day.empty and mask.any():
                    orb_levels[name] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
                else: orb_levels[name] = None

            # Simulation Minute Loop (Starts at 10:00)
            max_len = max(len(df) for df in day_dfs.values())
            for i in range(45, max_len):
                # 1. CHECK EXITS
                to_close = []
                for name, pos in self.active_positions.items():
                    df_day = day_dfs[name]
                    if i >= len(df_day): continue
                    
                    ltp = df_day['close'].iloc[i]
                    ts = df_day['date'].iloc[i]
                    ema9, ema21 = df_day['ema9'].iloc[i], df_day['ema21'].iloc[i]
                    
                    # Exit Reversal
                    exit_hit = (pos['type'] == 'LONG' and ema9 < ema21) or (pos['type'] == 'SHORT' and ema9 > ema21)
                    if exit_hit or ts.time() >= dt_time(15, 15):
                        pnl_pts = (ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)
                        self.all_trades.append({
                            'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF', 'Price': ltp, 
                            'PnL_Rs': round(pnl_pts * LOT_SIZES.get(name, 50), 2), 
                            'Reason': 'TECH_REVERSAL' if exit_hit else 'EOD'
                        })
                        to_close.append(name)
                
                for name in to_close: del self.active_positions[name]

                # 2. CHECK ENTRIES
                if len(self.active_positions) >= self.top_n: continue
                
                candidates = []
                for name, df_day in day_dfs.items():
                    if name in self.active_positions or i >= len(df_day): continue
                    
                    ltp = df_day['close'].iloc[i]
                    adx = df_day['adx'].iloc[i]
                    score = self._calc_score(name, ltp, adx, orb_levels[name], df_day.iloc[i])
                    
                    if abs(score) >= self.threshold:
                        candidates.append({'name': name, 'score': score, 'ltp': ltp, 'time': df_day['date'].iloc[i]})

                # Rank by absolute score
                ranked = sorted(candidates, key=lambda x: abs(x['score']), reverse=True)
                
                # Fill portfolio
                for c in ranked:
                    if len(self.active_positions) >= self.top_n: break
                    self.active_positions[c['name']] = {'in': c['ltp'], 'type': 'LONG' if c['score'] > 0 else 'SHORT', 'entry_time': c['time']}
                    self.all_trades.append({
                        'Time': c['time'], 'Stock': c['name'], 'Action': f"ENTRY ({self.active_positions[c['name']]['type']})", 
                        'Price': c['ltp'], 'PnL_Rs': '-', 'Reason': f"Score: {c['score']:.2f}"
                    })

    def _calc_score(self, name, ltp, adx, orb, row):
        if not orb: return 0
        f1 = 0.25 if ltp > orb['h'] else (-0.25 if ltp < orb['l'] else 0)
        f3 = 0.20 if row['ema5'] > row['ema9'] else -0.20 # Simple gap placeholder
        f8 = 0.25 if adx > 25 else 0
        # Weights: [F1, F2, F3, F4, F5, F6, F7, F8]
        # Applied to: [f1, 0, f3, 0, 0, 0, 0, f8]
        return (f1 * self.weights[0]) + (f3 * self.weights[2]) + (f8 * self.weights[7])

def run_portfolio_backtest():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    
    print("⏳ Loading data for all stocks...")
    stock_data = {}
    for s in top_stocks:
        loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
        df = loader.load_data(days=60)
        closes = df['close'].values.astype(float)
        df['ema5'] = talib.EMA(closes, 5)
        df['ema9'] = talib.EMA(closes, 9)
        df['ema21'] = talib.EMA(closes, 21)
        df['adx'] = talib.ADX(df['high'].values.astype(float), df['low'].values.astype(float), closes, 14)
        stock_data[s] = df

    for n_val in [5, 10, 1]:
        print(f"\n🚀 Running Real-Time Portfolio Simulation (Top {n_val})...")
        engine = RealtimePortfolioEngine(top_n=n_val)
        engine.run_simulation(stock_data)
        
        df_res = pd.DataFrame(engine.all_trades)
        pnl_sum = pd.to_numeric(df_res['PnL_Rs'], errors='coerce').sum()
        win_rate = (pd.to_numeric(df_res['PnL_Rs'], errors='coerce') > 0).mean() * 100
        print(f"✅ COMPLETED Top {n_val}: Total PnL: Rs {pnl_sum:,.2f} | Win Rate: {win_rate:.1f}%")
        
        # Save Report
        df_res.to_html(f"python-trader/backtest_lab/reports/realtime_portfolio_top{n_val}.html")

if __name__ == "__main__":
    os.makedirs("python-trader/backtest_lab/reports", exist_ok=True)
    run_portfolio_backtest()
