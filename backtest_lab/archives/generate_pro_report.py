import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.core.reporter import calculate_advanced_stats, generate_performance_charts

# Shared logic from previous iterations
from backtest_lab.generate_unified_matrix import UnifiedFastExitEngine, resample_data

def run_professional_study():
    stocks_dir = "backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    
    sample_df = pd.read_csv(os.path.join(stocks_dir, "RELIANCE_minute.csv"))
    all_dates = sorted(pd.to_datetime(sample_df['date']).dt.date.unique())[-7:]
    
    engine = UnifiedFastExitEngine(top_n=5)
    
    for d in all_dates:
        print(f"▶️ Simulating: {d}")
        stock_data_day = {}
        for s in top_stocks:
            loader = DataLoader(os.path.join(stocks_dir, f"{s}_minute.csv"))
            df = loader.load_data(days=20)
            df_5m, df_15m = resample_data(df, 5), resample_data(df, 15)
            df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 9)
            df_15m['ema5_15m'], df_15m['ema9_15m'], df_15m['ema20_15m'], df_15m['ema50_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5), talib.EMA(df_15m['close'].values.astype(float), 9), talib.EMA(df_15m['close'].values.astype(float), 20), talib.EMA(df_15m['close'].values.astype(float), 50)
            df_15m['adx_15m'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
            df = df.merge(df_5m[['date', 'ema9_5m']], on='date', how='left').ffill()
            df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m', 'ema20_15m', 'ema50_15m', 'adx_15m']], on='date', how='left').ffill()
            df_day = df[df['date'].dt.date == d].reset_index(drop=True)
            if df_day.empty: continue
            mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
            df_day.attrs['orb'] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
            stock_data_day[s] = df_day
        engine.run_simulation(stock_data_day)

    df_res = pd.DataFrame(engine.all_trades)
    reports_dir = "backtest_lab/reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    # 📊 Advanced Analytics
    stats = calculate_advanced_stats(df_res)
    chart_filename = generate_performance_charts(df_res, reports_dir)
    
    html_file = os.path.join(reports_dir, "professional_backtest_report.html")
    
    # 🏗️ Build HTML
    html_content = f"""
    <html>
    <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
            body {{ padding: 40px; background: #f4f7f6; font-family: 'Segoe UI', sans-serif; }}
            .stats-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
            .metric-label {{ color: #7f8c8d; font-size: 0.9rem; }}
            .metric-value {{ font-size: 1.2rem; font-weight: bold; color: #2c3e50; }}
            .chart-container {{ background: white; padding: 20px; border-radius: 10px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="mb-4">🛡️ Institutional Sniper Professional Report</h1>
            
            <div class="row g-3 mb-4">
                {''.join([f'<div class="col-md-3"><div class="stats-card"><div class="metric-label">{k}</div><div class="metric-value">{v}</div></div></div>' for k,v in stats.items()])}
            </div>

            <div class="chart-container text-center">
                <h3>📈 Performance Visuals</h3>
                <img src="{chart_filename}" class="img-fluid rounded">
            </div>

            <div class="mt-4 stats-card">
                <h3>📜 Transaction Ledger</h3>
                {df_res.to_html(classes='table table-sm table-striped table-hover')}
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(html_file, "w") as f:
        f.write(html_content)
    print(f"✅ Professional Report generated: {html_file}")

if __name__ == "__main__":
    run_professional_study()
