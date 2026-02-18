import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.generate_golden_week import GoldenWeekEngine, LOT_SIZES, resample_data

def generate_matrix_report():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    all_files = sorted([f for f in os.listdir(stocks_dir) if f.endswith('_minute.csv')])
    target_stocks = all_files[:50]
    
    # Dates
    sample_df = pd.read_csv(os.path.join(stocks_dir, target_stocks[0]))
    sample_df['date'] = pd.to_datetime(sample_df['date'])
    all_dates = sorted(sample_df['date'].dt.date.unique())
    golden_week_dates = all_dates[-7:]
    
    engine = GoldenWeekEngine(top_n=5)
    
    # Store daily pnl by stock: {stock: {date: pnl}}
    matrix_data = {s.replace('_minute.csv',''): {d.strftime('%Y-%m-%d'): 0 for d in golden_week_dates} for s in target_stocks}
    
    for d in golden_week_dates:
        print(f"▶️ Simulating: {d}")
        stock_data_day = {}
        for filename in target_stocks:
            stock_name = filename.replace('_minute.csv', '')
            loader = DataLoader(os.path.join(stocks_dir, filename))
            df = loader.load_data(days=20)
            df_15m = resample_data(df, 15)
            df_15m['ema5_15m'], df_15m['ema9_15m'], df_15m['ema20_15m'], df_15m['ema50_15m'] = talib.EMA(df_15m['close'].values.astype(float), 5), talib.EMA(df_15m['close'].values.astype(float), 9), talib.EMA(df_15m['close'].values.astype(float), 20), talib.EMA(df_15m['close'].values.astype(float), 50)
            df_15m['adx_15m'] = talib.ADX(df_15m['high'].values.astype(float), df_15m['low'].values.astype(float), df_15m['close'].values.astype(float), 14)
            df = df.merge(df_15m[['date', 'ema5_15m', 'ema9_15m', 'ema20_15m', 'ema50_15m', 'adx_15m']], on='date', how='left').ffill()
            df_day = df[df['date'].dt.date == d].reset_index(drop=True)
            if df_day.empty: continue
            mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
            df_day.attrs['orb'] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
            stock_data_day[stock_name] = df_day
            
        engine.run_simulation(stock_data_day)
        
        # Attribute PnL to the matrix for this specific day
        for t in engine.all_trades:
            # We only care about the SQUARE-OFF rows for PnL
            if t['Action'] == 'SQUARE-OFF':
                matrix_data[t['Stock']][d.strftime('%Y-%m-%d')] += t['PnL_Rs']
        
        # Clear engine trades for next day attribution
        engine.all_trades = []

    # 📊 Build Final Matrix DataFrame
    df_matrix = pd.DataFrame.from_dict(matrix_data, orient='index')
    df_matrix['Total'] = df_matrix.sum(axis=1)
    df_matrix = df_matrix.sort_values('Total', ascending=False)
    
    html_file = "python-trader/backtest_lab/reports/golden_week_matrix.html"
    
    html_content = f"""
    <html>
    <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
            body {{ padding: 40px; background: #fdfdfd; font-family: 'Inter', sans-serif; }}
            .profit {{ color: #27ae60; font-weight: bold; }}
            .loss {{ color: #c0392b; font-weight: bold; }}
            .table {{ background: white; border-radius: 10px; overflow: hidden; border: 1px solid #eee; }}
            th {{ background: #2c3e50 !important; color: white !important; text-align: center; }}
            td {{ text-align: right; }}
            .stock-col {{ text-align: left; font-weight: bold; background: #f9f9f9; }}
        </style>
    </head>
    <body>
        <h1 class="text-center mb-4">🗓️ Day-Wise Stock PnL Matrix (Golden Week)</h1>
        <div class="table-responsive">
            <table class="table table-hover table-bordered">
                <thead>
                    <tr>
                        <th>Stock</th>
                        {''.join([f'<th>{d.strftime("%d-%b")}</th>' for d in golden_week_dates])}
                        <th>Total PnL</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for stock, rows in df_matrix.iterrows():
        html_content += f"<tr><td class='stock-col'>{stock}</td>"
        for d in golden_week_dates:
            val = rows[d.strftime('%Y-%m-%d')]
            cls = 'profit' if val > 0 else ('loss' if val < 0 else '')
            html_content += f"<td class='{cls}'>{val:,.2f}</td>"
        
        tot = rows['Total']
        cls_tot = 'profit' if tot > 0 else ('loss' if tot < 0 else '')
        html_content += f"<td class='{cls_tot}' style='background:#f0f0f0;'>{tot:,.2f}</td></tr>"

    html_content += """
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    
    with open(html_file, "w") as f:
        f.write(html_content)
    print(f"✅ Matrix Report generated: {html_file}")

if __name__ == "__main__":
    os.makedirs("python-trader/backtest_lab/reports", exist_ok=True)
    generate_matrix_report()
