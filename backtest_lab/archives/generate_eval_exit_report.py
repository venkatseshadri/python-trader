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

class ExitEvaluatorEngine(MegaEngine):
    def run_day_eval_exit(self, df_day, stock_name):
        if df_day.empty: return
        window_end = dt_time(10, 0)
        lot_size = LOT_SIZES.get(stock_name, 50)
        
        orb_mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= window_end)
        if orb_mask.any():
            self.orb_high = df_day.loc[orb_mask, 'high'].max()
            self.orb_low = df_day.loc[orb_mask, 'low'].min()
        else: return

        closes = df_day['close'].values.astype(float)
        ema5 = talib.EMA(closes, 5)
        ema9 = talib.EMA(closes, 9)
        adx = talib.ADX(df_day['high'].values.astype(float), df_day['low'].values.astype(float), closes, 14)
        dates = df_day['date'].values
        
        position = None
        trades_today = 0
        for i in range(30, len(df_day)):
            ltp = closes[i]
            ts = pd.Timestamp(dates[i])
            
            if position:
                # 🧠 EXIT EVALUATOR LOGIC
                exit_score = 0
                reasons = []
                
                # Filter 1: EMA 5/9 Reversal (-0.40)
                if (position['type'] == 'LONG' and ema5[i] < ema9[i]) or (position['type'] == 'SHORT' and ema5[i] > ema9[i]):
                    exit_score -= 0.40
                    reasons.append("EMA_5/9_CROSS")
                
                # Filter 2: Price Position (-0.20)
                if (position['type'] == 'LONG' and ltp < ema9[i]) or (position['type'] == 'SHORT' and ltp > ema9[i]):
                    exit_score -= 0.20
                    reasons.append("PRICE_VS_EMA9")
                
                # Filter 3: ADX Momentum Loss (-0.20)
                if adx[i] < 20:
                    exit_score -= 0.20
                    reasons.append("LOW_ADX")

                # EXIT CONDITION: Score <= -0.50 (at least two signals)
                do_exit = exit_score <= -0.50 or ts.time() >= dt_time(15, 15)
                
                if do_exit:
                    final_reason = " | ".join(reasons) if exit_score <= -0.50 else "EOD"
                    pnl_pts = (ltp - position['entry_spot']) if position['type'] == 'LONG' else (position['entry_spot'] - ltp)
                    
                    self.trades.append({
                        'Time': position['entry_time'], 'Stock': stock_name, 'Action': f"ENTRY ({position['type']})",
                        'Price': position['entry_spot'], 'PnL_Rs': '-', 'Reason': f"ADX: {position['adx']:.1f}"
                    })
                    self.trades.append({
                        'Time': ts, 'Stock': stock_name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_pts * lot_size, 2), 'Reason': f"EXIT_SCORE: {exit_score:.2f} ({final_reason})"
                    })
                    position = None
                continue

            if ts.time() <= window_end or ts.time() > dt_time(14,30) or trades_today >= 1: continue
            
            if adx[i] > 25:
                if self.orb_high and ltp > self.orb_high:
                    position = {'entry_time': ts, 'entry_spot': ltp, 'type': 'LONG', 'adx': adx[i]}
                    trades_today += 1
                elif self.orb_low and ltp < self.orb_low:
                    position = {'entry_time': ts, 'entry_spot': ltp, 'type': 'SHORT', 'adx': adx[i]}
                    trades_today += 1

def generate_eval_exit_report():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    stock_files = [os.path.join(stocks_dir, f"{s}_minute.csv") for s in top_stocks]
    
    engine = ExitEvaluatorEngine(None)
    all_rows = []
    
    for f in stock_files:
        stock_name = os.path.basename(f).replace('_minute.csv', '')
        loader = DataLoader(f)
        df = loader.load_data(days=60)
        day_groups = [g for _, group in df.groupby(df['date'].dt.date) for g in [group]]
        engine.reset()
        for df_day in day_groups:
            engine.run_day_eval_exit(df_day, stock_name)
        all_rows.extend(engine.trades)

    df_report = pd.DataFrame(all_rows)
    df_report['numeric_pnl'] = pd.to_numeric(df_report['PnL_Rs'], errors='coerce').fillna(0)
    summary = df_report.groupby('Stock').agg({'numeric_pnl': 'sum', 'Action': lambda x: sum(1 for a in x if 'ENTRY' in a)}).rename(columns={'numeric_pnl': 'Total Profit (Rs)', 'Action': 'Total Trades'})
    
    # Simple HTML assembly
    html_content = f"<html><head><link rel='stylesheet' href='https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css'></head><body class='p-5'>"
    html_content += f"<h1 class='text-center'>🛡️ Exit Evaluator Report (Soft-Exit Logic)</h1>"
    html_content += f"<div class='card p-4 mb-4'><h3>Portfolio PnL: Rs {summary['Total Profit (Rs)'].sum():,.2f}</h3>{summary.to_html(classes='table')}</div>"
    html_content += f"<div class='card p-4'><h3>Transaction Log</h3>{df_report.to_html(classes='table table-sm')}</div>"
    html_content += "</body></html>"
    
    with open("python-trader/backtest_lab/reports/eval_exit_report.html", "w") as f:
        f.write(html_content)
    print(f"✅ Exit Evaluator Report generated: python-trader/backtest_lab/reports/eval_exit_report.html")

if __name__ == "__main__":
    generate_eval_exit_report()
