import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.nifty50_realtime_portfolio import RealtimePortfolioEngine, LOT_SIZES

def generate_full_day_html(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    all_files = sorted([f for f in os.listdir(stocks_dir) if f.endswith('_minute.csv')])
    target_stocks = all_files[:50]
    
    target_date = pd.to_datetime(target_date_str).date()
    
    print(f"⏳ Loading data for 50 stocks for {target_date_str}...")
    stock_data = {}
    for filename in target_stocks:
        stock_name = filename.replace('_minute.csv', '')
        loader = DataLoader(os.path.join(stocks_dir, filename))
        df = loader.load_data(days=10) # 10 days for indicator warm-up
        
        closes = df['close'].values.astype(float)
        df['ema5'] = talib.EMA(closes, 5)
        df['ema9'] = talib.EMA(closes, 9)
        df['ema21'] = talib.EMA(closes, 21)
        df['adx'] = talib.ADX(df['high'].values.astype(float), df['low'].values.astype(float), closes, 14)
        
        # Keep only the target day
        stock_data[stock_name] = df[df['date'].dt.date == target_date].reset_index(drop=True)

    print(f"🚀 Running Full-Day 50-Stock Portfolio Simulation...")
    engine = RealtimePortfolioEngine(top_n=5, threshold=0.35)
    engine.run_simulation(stock_data)
    
    df_trades = pd.DataFrame(engine.all_trades)
    if df_trades.empty:
        print("No trades were taken on this day.")
        return

    # Calculate PnL Summary
    numeric_pnl = pd.to_numeric(df_trades['PnL_Rs'], errors='coerce').fillna(0)
    df_trades['numeric_pnl'] = numeric_pnl
    total_pnl = df_trades['numeric_pnl'].sum()
    
    html_content = f"""
    <html>
    <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
            body {{ background-color: #f0f2f5; padding: 40px; font-family: 'Inter', sans-serif; }}
            .card {{ border-radius: 15px; border: none; box-shadow: 0 8px 16px rgba(0,0,0,0.1); margin-bottom: 30px; }}
            .entry-row {{ background-color: #e3f2fd !important; }}
            .exit-row {{ background-color: #fff3e0 !important; border-bottom: 2px solid #ddd !important; }}
            .profit {{ color: #2e7d32; font-weight: bold; }}
            .loss {{ color: #d32f2f; font-weight: bold; }}
            .summary-header {{ background: #1a237e; color: white; padding: 30px; border-radius: 15px; margin-bottom: 30px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="summary-header text-center">
                <h1>🦅 NIFTY 50 SNAPSHOT REPORT</h1>
                <h3>Date: {target_date_str} | Selection: Top 5 | Universe: 50 Stocks</h3>
                <h2 class="mt-3">Total Day PnL: <span style="color: {'#81c784' if total_pnl > 0 else '#ff8a80'}">Rs {total_pnl:,.2f}</span></h2>
            </div>

            <div class="card p-4">
                <h4 class="mb-3">📜 Transaction Timeline</h4>
                <table class="table table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Time</th>
                            <th>Stock</th>
                            <th>Action</th>
                            <th>Price</th>
                            <th>PnL (Rs)</th>
                            <th>Logic/Reason</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for i, row in df_trades.iterrows():
        is_entry = "ENTRY" in row['Action']
        row_class = "entry-row" if is_entry else "exit-row"
        pnl_val = row['numeric_pnl']
        pnl_display = f"{pnl_val:,.2f}" if not is_entry else "-"
        pnl_class = "profit" if pnl_val > 0 else "loss"
        
        html_content += f"""
                        <tr class="{row_class}">
                            <td>{row['Time'].strftime('%H:%M:%S')}</td>
                            <td>{row['Stock']}</td>
                            <td>{row['Action']}</td>
                            <td>{row['Price']:.2f}</td>
                            <td class="{pnl_class if not is_entry else ''}">{pnl_display}</td>
                            <td>{row['Reason']}</td>
                        </tr>
        """

    html_content += """
                    </tbody>
                </table>
            </div>
        </div>
    </body>
    </html>
    """
    
    report_path = f"python-trader/backtest_lab/reports/nifty50_day_report_{target_date_str}.html"
    with open(report_path, "w") as f:
        f.write(html_content)
    print(f"✅ Full-Day HTML report generated: {report_path}")

if __name__ == "__main__":
    os.makedirs("python-trader/backtest_lab/reports", exist_ok=True)
    generate_full_day_html("2026-01-21")
