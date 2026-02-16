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

class TransactionEngine(MegaEngine):
    def run_day_transaction(self, df_day):
        if df_day.empty: return
        window_end = dt_time(10, 0)
        
        orb_mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= window_end)
        if orb_mask.any():
            self.orb_high = df_day.loc[orb_mask, 'high'].max()
            self.orb_low = df_day.loc[orb_mask, 'low'].min()
        else: return

        closes = df_day['close'].values.astype(float)
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
                exit_hit = (position['type'] == 'LONG' and ema9[i] < ema21[i]) or (position['type'] == 'SHORT' and ema9[i] > ema21[i])
                if exit_hit or ts.time() >= dt_time(15, 15):
                    reason = f'TECH_REVERSAL' if exit_hit else 'EOD'
                    pnl = (ltp - position['entry_spot']) if position['type'] == 'LONG' else (position['entry_spot'] - ltp)
                    
                    # 1. Create ENTRY row
                    self.trades.append({
                        'Time': position['entry_time'], 'Stock': position['stock'], 
                        'Action': f"ENTRY ({position['type']})", 'Price': position['entry_spot'], 'PnL': '-'
                    })
                    # 2. Create SQUARE-OFF row
                    self.trades.append({
                        'Time': ts, 'Stock': position['stock'], 
                        'Action': 'SQUARE-OFF', 'Price': ltp, 'PnL': round(pnl * 50, 2), 'Reason': reason
                    })
                    position = None
                continue

            if ts.time() <= window_end or ts.time() > dt_time(14,30) or trades_today >= 1: continue
            
            if adx[i] > 25:
                if self.orb_high and ltp > self.orb_high:
                    position = {'entry_time': ts, 'entry_spot': ltp, 'type': 'LONG', 'stock': self.current_stock}
                    trades_today += 1
                elif self.orb_low and ltp < self.orb_low:
                    position = {'entry_time': ts, 'entry_spot': ltp, 'type': 'SHORT', 'stock': self.current_stock}
                    trades_today += 1

def generate_transaction_report():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "LT", "SBIN", "HDFCBANK"]
    stock_files = [os.path.join(stocks_dir, f"{s}_minute.csv") for s in top_stocks]
    
    engine = TransactionEngine(None)
    all_rows = []
    
    print(f"📊 Generating transaction-level report for top 5 stocks...")
    
    for f in stock_files:
        engine.current_stock = os.path.basename(f).replace('_minute.csv', '')
        loader = DataLoader(f)
        df = loader.load_data(days=30)
        day_groups = [g for _, group in df.groupby(df['date'].dt.date) for g in [group]]
        engine.reset()
        for df_day in day_groups:
            engine.run_day_transaction(df_day)
        all_rows.extend(engine.trades)

    df_report = pd.DataFrame(all_rows)
    
    html_content = f"""
    <html>
    <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
            body {{ background-color: #f8f9fa; padding: 40px; }}
            .entry-row {{ background-color: #e8f4fd !important; }}
            .exit-row {{ background-color: #fdf2e8 !important; border-bottom: 2px solid #dee2e6 !important; }}
            .table {{ background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <h1 class="text-center mb-4">📜 Detailed Transaction Log (ORB Sniper)</h1>
            <p class="text-muted text-center">Each trade is split into ENTRY and SQUARE-OFF events.</p>
            
            <table class="table table-hover">
                <thead class="table-dark">
                    <tr>
                        <th>Time</th>
                        <th>Stock</th>
                        <th>Action</th>
                        <th>Price</th>
                        <th>PnL (Rs)</th>
                        <th>Reason/Notes</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for i, row in df_report.iterrows():
        row_class = "entry-row" if "ENTRY" in row['Action'] else "exit-row"
        pnl_val = row['PnL']
        pnl_class = "text-success fw-bold" if isinstance(pnl_val, (int, float)) and pnl_val > 0 else ("text-danger fw-bold" if isinstance(pnl_val, (int, float)) and pnl_val < 0 else "")
        
        html_content += f"""
                    <tr class="{row_class}">
                        <td>{row['Time']}</td>
                        <td>{row['Stock']}</td>
                        <td>{row['Action']}</td>
                        <td>{row['Price']:.2f}</td>
                        <td class="{pnl_class}">{pnl_val}</td>
                        <td>{row.get('Reason', '-')}</td>
                    </tr>
        """

    html_content += """
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    
    report_path = "python-trader/backtest_lab/reports/transaction_log_report.html"
    with open(report_path, "w") as f:
        f.write(html_content)
    print(f"✅ Transaction report generated: {report_path}")

if __name__ == "__main__":
    generate_transaction_report()
