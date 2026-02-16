import pandas as pd
import numpy as np
import talib
import os
import sys
import json
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.mega_stock_optimizer import MegaEngine

# 1. LOT SIZES (Extracted from symbol map)
LOT_SIZES = {"ZYDUSLIFE": 900, "WIPRO": 3000, "VEDL": 1150, "VBL": 1125, "UNITDSPR": 400, "ULTRACEMCO": 50, "TVSMOTOR": 175, "TRENT": 100, "TORNTPHARM": 250, "TITAN": 175, "TECHM": 600, "TCS": 175, "TATASTEEL": 5500, "TATAPOWER": 1450, "TATACONSUM": 550, "SUNPHARMA": 350, "SOLARINDS": 50, "SIEMENS": 175, "SHRIRAMFIN": 825, "SHREECEM": 25, "SBIN": 750, "SBILIFE": 375, "RELIANCE": 250, "RECLTD": 1400, "POWERGRID": 1900, "PNB": 8000, "PIDILITIND": 500, "PFC": 1300, "ONGC": 2250, "NTPC": 1500, "NHPC": 6400, "NESTLEIND": 500, "NAUKRI": 375, "MUTHOOTFIN": 275, "MOTHERSON": 6150, "MARUTI": 50, "M&M": 200, "LUPIN": 425, "LTIM": 150, "LT": 175, "LICI": 700, "KOTAKBANK": 400, "JSWSTEEL": 675, "JINDALSTEL": 625, "ITC": 1600, "IOC": 4875, "INFY": 400, "INDUSINDBK": 700, "INDIGO": 150, "INDHOTEL": 1000, "ICICIPRULI": 925, "ICICIGI": 325, "ICICIBANK": 700, "HINDUNILVR": 300, "HINDALCO": 700, "HEROMOTOCO": 150, "HDFCLIFE": 1100, "HDFCBANK": 550, "HCLTECH": 350, "HAVELLS": 500, "HAL": 150, "GRASIM": 250, "GAIL": 3150, "EICHERMOT": 100, "DRREDDY": 625, "DMART": 150, "DLF": 825, "DIVISLAB": 100, "DABUR": 1250, "COALINDIA": 1350, "CIPLA": 375, "CHOLAFIN": 625, "CANBK": 6750, "BRITANNIA": 125, "BPCL": 1975, "BOSCHLTD": 25, "BHEL": 2625, "BHARTIARTL": 475, "BEL": 1425, "BANKBARODA": 2925, "BAJFINANCE": 125, "BAJAJHLDNG": 50, "BAJAJFINSV": 500, "BAJAJ-AUTO": 125, "AXISBANK": 625, "ASIANPAINT": 200, "APOLLOHOSP": 125, "AMBUJACEM": 1050, "ADANIPORTS": 475, "ADANIENT": 300, "ABB": 125}

class AdvancedMasterEngine(MegaEngine):
    def run_day_master(self, df_day, stock_name):
        if df_day.empty: return
        window_end = dt_time(10, 0)
        tp_pct = 1.0
        sl_pct = 2.0
        lot_size = LOT_SIZES.get(stock_name, 50) # Fallback to 50 if unknown
        
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
                pnl_pct = (ltp - position['entry_spot']) / position['entry_spot'] * 100
                if position['type'] == 'SHORT': pnl_pct = -pnl_pct
                position['max_pnl_pct'] = max(position.get('max_pnl_pct', 0), pnl_pct)
                
                # Exit Checks
                reason = None
                if pnl_pct >= tp_pct: reason = f"TP HIT (+{pnl_pct:.2f}%)"
                elif pnl_pct <= -sl_pct: reason = f"SL HIT ({pnl_pct:.2f}%)"
                elif (position['type'] == 'LONG' and ema9[i] < ema21[i]) or (position['type'] == 'SHORT' and ema9[i] > ema21[i]):
                    reason = f"TECH REVERSAL (EMA 9/21)"
                elif ts.time() >= dt_time(15, 15):
                    reason = "EOD SQUARE-OFF"

                if reason:
                    pnl_pts = (ltp - position['entry_spot']) if position['type'] == 'LONG' else (position['entry_spot'] - ltp)
                    pnl_rs = pnl_pts * lot_size
                    
                    # 1. ENTRY ROW
                    self.trades.append({
                        'Time': position['entry_time'], 'Stock': stock_name, 'Action': f"ENTRY ({position['type']})",
                        'Price': position['entry_spot'], 'PnL_Rs': '-', 'Reason': f"ADX: {position['adx']:.1f}, ORB_H: {self.orb_high:.1f}"
                    })
                    # 2. EXIT ROW
                    self.trades.append({
                        'Time': ts, 'Stock': stock_name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_rs, 2), 'Reason': reason
                    })
                    position = None
                continue

            if ts.time() <= window_end or ts.time() > dt_time(14,30) or trades_today >= 1: continue
            
            if adx[i] > 25:
                side = None
                if ltp > self.orb_high: side = 'LONG'
                elif ltp < self.orb_low: side = 'SHORT'
                
                if side:
                    position = {'entry_time': ts, 'entry_spot': ltp, 'type': side, 'adx': adx[i]}
                    trades_today += 1

def generate_master_report():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    stock_files = [os.path.join(stocks_dir, f"{s}_minute.csv") for s in top_stocks]
    
    engine = AdvancedMasterEngine(None)
    all_rows = []
    
    print(f"📊 Generating MASTER report for Top 10 stocks...")
    
    for f in stock_files:
        stock_name = os.path.basename(f).replace('_minute.csv', '')
        loader = DataLoader(f)
        df = loader.load_data(days=60)
        day_groups = [g for _, group in df.groupby(df['date'].dt.date) for g in [group]]
        engine.reset()
        for df_day in day_groups:
            engine.run_day_master(df_day, stock_name)
        all_rows.extend(engine.trades)

    df_report = pd.DataFrame(all_rows)
    
    # Calculate Summary
    numeric_pnl = pd.to_numeric(df_report['PnL_Rs'], errors='coerce').fillna(0)
    df_report['numeric_pnl'] = numeric_pnl
    summary = df_report.groupby('Stock').agg({'numeric_pnl': 'sum', 'Action': lambda x: sum(1 for a in x if 'ENTRY' in a)}).rename(columns={'numeric_pnl': 'Total Profit (Rs)', 'Action': 'Total Trades'})
    
    html_content = f"""
    <html>
    <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
            body {{ background-color: #f8f9fa; padding: 40px; font-family: 'Segoe UI', sans-serif; }}
            .card {{ border-radius: 12px; border: none; box-shadow: 0 6px 12px rgba(0,0,0,0.08); margin-bottom: 30px; }}
            .entry-row {{ background-color: #f0f7ff !important; border-left: 4px solid #007bff; }}
            .exit-row {{ background-color: #fff9f0 !important; border-left: 4px solid #fd7e14; border-bottom: 2px solid #eee; }}
            .profit {{ color: #28a745; font-weight: bold; }}
            .loss {{ color: #dc3545; font-weight: bold; }}
            .header-bar {{ background: #212529; color: white; padding: 20px; border-radius: 12px; margin-bottom: 30px; }}
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <div class="header-bar text-center">
                <h1>🎯 ORBITER MASTER TRADING REPORT</h1>
                <p>90 Days | 10 Stocks | 10:00 AM Sniper | Corrected Lot Sizes & Exit Reasons</p>
            </div>

            <div class="card p-4">
                <h3 class="mb-3">🏁 Portfolio Summary (Per Stock)</h3>
                {summary.sort_values('Total Profit (Rs)', ascending=False).to_html(classes='table table-hover table-bordered')}
                <div class="mt-3">
                    <h4>Total Portfolio PnL: <span class="{'profit' if summary['Total Profit (Rs)'].sum() > 0 else 'loss'}">Rs {summary['Total Profit (Rs)'].sum():,.2f}</span></h4>
                </div>
            </div>

            <div class="card p-4">
                <h3 class="mb-3">📜 Complete Transaction Log</h3>
                <table class="table table-sm">
                    <thead class="table-dark">
                        <tr>
                            <th>Time</th>
                            <th>Stock</th>
                            <th>Action</th>
                            <th>Price</th>
                            <th>PnL (Rs)</th>
                            <th>Detailed Reason</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for i, row in df_report.iterrows():
        is_entry = "ENTRY" in row['Action']
        row_class = "entry-row" if is_entry else "exit-row"
        pnl_val = row['PnL_Rs']
        pnl_display = f"{pnl_val:,.2f}" if not is_entry else "-"
        pnl_class = ""
        if not is_entry:
            pnl_class = "profit" if pnl_val > 0 else "loss"
            
        html_content += f"""
                        <tr class="{row_class}">
                            <td>{row['Time']}</td>
                            <td>{row['Stock']}</td>
                            <td>{row['Action']}</td>
                            <td>{row['Price']:.2f}</td>
                            <td class="{pnl_class}">{pnl_display}</td>
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
    
    with open("python-trader/backtest_lab/reports/master_trading_report.html", "w") as f:
        f.write(html_content)
    print(f"✅ Master HTML report generated: python-trader/backtest_lab/reports/master_trading_report.html")

if __name__ == "__main__":
    generate_master_report()
