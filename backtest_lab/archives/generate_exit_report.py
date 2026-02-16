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

class DualExitEngine(MegaEngine):
    def run_day_dual(self, df_day, exit_type='5/9'):
        if df_day.empty: return
        window_end = dt_time(10, 0)
        
        orb_mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= window_end)
        if orb_mask.any():
            self.orb_high = df_day.loc[orb_mask, 'high'].max()
            self.orb_low = df_day.loc[orb_mask, 'low'].min()
        else: return

        closes = df_day['close'].values.astype(float)
        ema5 = talib.EMA(closes, 5)
        ema9 = talib.EMA(closes, 9)
        ema21 = talib.EMA(closes, 21)
        adx = talib.ADX(df_day['high'].values.astype(float), df_day['low'].values.astype(float), closes, 14)
        dates = df_day['date'].values
        
        position = None
        trades_today = 0
        for i in range(30, len(df_day)):
            ltp = closes[i]
            ts = pd.Timestamp(dates[i])
            
            if position:
                pnl_pct = (ltp - position['entry_spot']) / position['entry_spot'] * 100
                if position['type'] == 'SHORT': pnl_pct = -pnl_pct
                
                # Dynamic Exit Choice
                exit_hit = False
                if exit_type == '5/9':
                    exit_hit = (position['type'] == 'LONG' and ema5[i] < ema9[i]) or (position['type'] == 'SHORT' and ema5[i] > ema9[i])
                else: # 9/21
                    exit_hit = (position['type'] == 'LONG' and ema9[i] < ema21[i]) or (position['type'] == 'SHORT' and ema9[i] > ema21[i])
                
                if exit_hit:
                    self._close(position, ltp, ts, f'TECH_{exit_type}', pnl_pct * 50)
                elif ts.time() >= dt_time(15, 15):
                    self._close(position, ltp, ts, 'EOD', pnl_pct * 50)

                if position['status'] == 'CLOSED':
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

def generate_dual_exit_report():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT"]
    stock_files = [os.path.join(stocks_dir, f"{s}_minute.csv") for s in top_stocks]
    
    results = []
    
    for exit_mode in ['5/9', '9/21']:
        engine = DualExitEngine(None)
        all_trades = []
        for f in stock_files:
            stock_name = os.path.basename(f).replace('_minute.csv', '')
            loader = DataLoader(f)
            df = loader.load_data(days=60)
            day_groups = [g for _, group in df.groupby(df['date'].dt.date) for g in [group]]
            engine.reset()
            for df_day in day_groups:
                engine.run_day_dual(df_day, exit_type=exit_mode)
                engine.finalize_day(df_day['date'].iloc[0].date())
            for t in engine.trades:
                t['stock'] = stock_name
                t['mode'] = exit_mode
                all_trades.append(t)
        results.extend(all_trades)

    df = pd.DataFrame(results)
    df['pnl_rs'] = df['pnl'] * 50
    
    summary = df.groupby('mode').agg({'pnl_rs': 'sum', 'pnl': 'count'}).rename(columns={'pnl': 'Total Trades'})
    
    html_content = f"""
    <html>
    <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
            body {{ background-color: #f4f7f6; padding: 30px; }}
            .summary-card {{ background: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            .profit {{ color: #2ecc71; }}
            .loss {{ color: #e74c3c; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="text-center mb-5">⚖️ Technical Exit Comparison Report</h1>
            
            <div class="row">
                <div class="col-md-12">
                    <div class="summary-card">
                        <h3>Strategy Summary</h3>
                        {summary.to_html(classes='table table-bordered')}
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <div class="summary-card">
                        <h4 class="text-primary">Sensitive Exit (EMA 5/9)</h4>
                        <p>Total PnL: <span class="{'profit' if summary.loc['5/9','pnl_rs'] > 0 else 'loss'}">Rs {summary.loc['5/9','pnl_rs']:,.2f}</span></p>
                        <p>Trades: {summary.loc['5/9','Total Trades']}</p>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="summary-card">
                        <h4 class="text-success">Robust Exit (EMA 9/21)</h4>
                        <p>Total PnL: <span class="{'profit' if summary.loc['9/21','pnl_rs'] > 0 else 'loss'}">Rs {summary.loc['9/21','pnl_rs']:,.2f}</span></p>
                        <p>Trades: {summary.loc['9/21','Total Trades']}</p>
                    </div>
                </div>
            </div>

            <div class="summary-card">
                <h4>Detailed Trade Log (Last 20)</h4>
                {df.tail(20)[['entry_time', 'stock', 'mode', 'type', 'pnl_rs', 'reason']].to_html(classes='table table-striped')}
            </div>
        </div>
    </body>
    </html>
    """
    
    with open("python-trader/backtest_lab/reports/exit_comparison_report.html", "w") as f:
        f.write(html_content)
    print(f"✅ Comparison HTML report generated: python-trader/backtest_lab/reports/exit_comparison_report.html")

if __name__ == "__main__":
    generate_dual_exit_report()
