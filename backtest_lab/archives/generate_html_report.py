import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader
from backtest_lab.adx_one_year_study import ADXExtendedEngine, calc_stats
from backtest_lab.mega_stock_optimizer import MegaEngine

class HTMLReportEngine(MegaEngine):
    def run_day_sniper(self, df_day, window_end, use_adx=True):
        if df_day.empty: return
        orb_mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= window_end)
        if orb_mask.any():
            self.orb_high = df_day.loc[orb_mask, 'high'].max()
            self.orb_low = df_day.loc[orb_mask, 'low'].min()
        else: self.orb_high = self.orb_low = None

        closes = df_day['close'].values.astype(float)
        ema5 = talib.EMA(closes, 5)
        ema9 = talib.EMA(closes, 9)
        adx = talib.ADX(df_day['high'].values.astype(float), df_day['low'].values.astype(float), closes, 14)
        
        position = None
        trades_today = 0
        for i in range(30, len(df_day)):
            ltp = closes[i]
            ts = pd.Timestamp(df_day['date'].iloc[i])
            if position:
                pnl_rs = self._calc_pnl_rs(position, ltp)
                if (position['type'] == 'LONG' and ema5[i] < ema9[i]) or (position['type'] == 'SHORT' and ema5[i] > ema9[i]):
                    self._close(position, ltp, ts, 'TECH_REVERSAL', pnl_rs)
                if position['status'] == 'CLOSED':
                    self.trades.append(position)
                    position = None
                continue
            if ts.time() <= window_end or ts.time() > dt_time(14,30) or trades_today >= 1: continue
            
            is_trending = adx[i] > 25
            if self.orb_high and ltp > self.orb_high and is_trending:
                position = {'entry_time': ts, 'entry_spot': ltp, 'type': 'LONG', 'status': 'OPEN', 'max_pnl_rs': 0, 'lot_size': 50}
                trades_today += 1
            elif self.orb_low and ltp < self.orb_low and is_trending:
                position = {'entry_time': ts, 'entry_spot': ltp, 'type': 'SHORT', 'status': 'OPEN', 'max_pnl_rs': 0, 'lot_size': 50}
                trades_today += 1

def generate_html_report():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    stock_files = [os.path.join(stocks_dir, f"{s}_minute.csv") for s in top_stocks]
    
    engine = HTMLReportEngine(None, config={'weights':[1,0,0,0,0,0,0,0], 'trade_threshold':0.20, 'sl_pct':10, 'tsl_retracement_pct':30, 'tsl_activation_rs':1000})
    all_trades = []
    
    for f in stock_files:
        stock_name = os.path.basename(f).replace('_minute.csv', '')
        loader = DataLoader(f)
        df = loader.load_data(days=90)
        day_groups = [g for _, group in df.groupby(df['date'].dt.date) for g in [group]]
        engine.reset()
        for df_day in day_groups:
            engine.run_day_sniper(df_day, dt_time(10,0))
            engine.finalize_day(df_day['date'].iloc[0].date())
        for t in engine.trades:
            t['stock'] = stock_name
            all_trades.append(t)

    df_trades = pd.DataFrame(all_trades)
    df_trades['pnl_rs'] = df_trades['pnl'] * 50
    df_trades['month'] = df_trades['entry_time'].dt.strftime('%Y-%m')
    
    # Aggregates
    stock_perf = df_trades.groupby('stock').agg({'pnl_rs': 'sum', 'pnl': 'count'}).rename(columns={'pnl': 'Trades'}).to_html(classes='table table-striped')
    monthly_perf = df_trades.groupby('month').agg({'pnl_rs': 'sum'}).to_html(classes='table table-dark')
    
    total_profit = df_trades['pnl_rs'].sum()
    win_rate = (df_trades['pnl_rs'] > 0).mean() * 100

    html_content = f"""
    <html>
    <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
            body {{ background-color: #f8f9fa; padding: 20px; font-family: sans-serif; }}
            .card {{ margin-bottom: 20px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
            .profit {{ color: green; font-weight: bold; }}
            .loss {{ color: red; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="text-center mb-4">🚀 ORBITER Sniper Report (10:00 AM Window)</h1>
            
            <div class="row">
                <div class="col-md-4">
                    <div class="card p-3 text-center">
                        <h3>Overall Profit</h3>
                        <h2 class="{'profit' if total_profit > 0 else 'loss'}">Rs {total_profit:,.2f}</h2>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card p-3 text-center">
                        <h3>Win Rate</h3>
                        <h2>{win_rate:.1f}%</h2>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card p-3 text-center">
                        <h3>Total Trades</h3>
                        <h2>{len(df_trades)}</h2>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <div class="card p-3">
                        <h4 class="mb-3">Stock-wise Performance</h4>
                        {stock_perf}
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card p-3">
                        <h4 class="mb-3">Monthly Trends</h4>
                        {monthly_perf}
                    </div>
                </div>
            </div>
            
            <div class="card p-3">
                <h4>Recent 50 Trades</h4>
                {df_trades.tail(50)[['entry_time', 'stock', 'type', 'entry_spot', 'exit_spot', 'pnl_rs', 'reason']].to_html(classes='table table-sm')}
            </div>
        </div>
    </body>
    </html>
    """
    
    with open("python-trader/backtest_lab/reports/sniper_detailed_report.html", "w") as f:
        f.write(html_content)
    
    print(f"✅ Detailed HTML report generated: python-trader/backtest_lab/reports/sniper_detailed_report.html")

if __name__ == "__main__":
    os.makedirs("python-trader/backtest_lab/reports", exist_ok=True)
    generate_html_report()
