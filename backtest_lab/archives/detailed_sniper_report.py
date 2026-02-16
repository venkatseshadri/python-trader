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

class DetailedReportEngine(MegaEngine):
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
        dates = df_day['date'].values
        
        position = None
        trades_today = 0
        for i in range(30, len(df_day)):
            ltp = closes[i]
            ts = pd.Timestamp(dates[i])
            if position:
                pnl_rs = self._calc_pnl_rs(position, ltp)
                if (position['type'] == 'LONG' and ema5[i] < ema9[i]) or (position['type'] == 'SHORT' and ema5[i] > ema9[i]):
                    self._close(position, ltp, ts, 'TECH_REVERSAL', pnl_rs)
                if position['status'] == 'CLOSED':
                    self.trades.append(position)
                    position = None
                continue
            if ts.time() <= window_end or ts.time() > dt_time(14,30) or trades_today >= 1: continue
            
            is_trending = adx[i] > 25 if use_adx else True
            score = 0
            if self.orb_high and ltp > self.orb_high and is_trending: score = 0.25
            elif self.orb_low and ltp < self.orb_low and is_trending: score = -0.25
            
            if score != 0:
                position = {'entry_time': ts, 'entry_spot': ltp, 'type': 'LONG' if score > 0 else 'SHORT', 'status': 'OPEN', 'max_pnl_rs': 0, 'lot_size': 50}
                trades_today += 1

def generate_detailed_report():
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    top_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "AXISBANK", "BHARTIARTL", "KOTAKBANK"]
    stock_files = [os.path.join(stocks_dir, f"{s}_minute.csv") for s in top_stocks]
    
    engine = DetailedReportEngine(None, config={'weights':[1,0,0,0,0,0,0,0], 'trade_threshold':0.20, 'sl_pct':10, 'tsl_retracement_pct':30, 'tsl_activation_rs':1000})
    
    all_trades = []
    
    print(f"📊 Generating detailed report for Top 10 stocks (90 Days)...")
    
    for f in stock_files:
        stock_name = os.path.basename(f).replace('_minute.csv', '')
        loader = DataLoader(f)
        df = loader.load_data(days=90)
        day_groups = [g for _, group in df.groupby(df['date'].dt.date) for g in [group]]
        
        engine.reset()
        for df_day in day_groups:
            engine.run_day_sniper(df_day, dt_time(10,0), use_adx=True)
            engine.finalize_day(df_day['date'].iloc[0].date())
            
        for t in engine.trades:
            t['stock'] = stock_name
            all_trades.append(t)

    trade_df = pd.DataFrame(all_trades)
    trade_df['month'] = trade_df['entry_time'].dt.strftime('%Y-%m')
    trade_df['pnl_rs'] = trade_df['pnl'] * 50
    
    # 1. STOCK PERFORMANCE
    stock_summary = trade_df.groupby('stock').agg({
        'pnl_rs': 'sum',
        'pnl': lambda x: (x > 0).mean() * 100,
        'entry_time': 'count'
    }).rename(columns={'pnl_rs': 'Total Profit (Rs)', 'pnl': 'Win %', 'entry_time': 'Total Trades'})
    
    # 2. MONTHLY PERFORMANCE
    monthly_summary = trade_df.groupby('month').agg({
        'pnl_rs': 'sum',
        'pnl': lambda x: (x > 0).mean() * 100
    }).rename(columns={'pnl_rs': 'Monthly Profit (Rs)', 'pnl': 'Win %'})

    print("\n" + "="*60)
    print("🏆 STOCK-BY-STOCK PERFORMANCE BREAKDOWN")
    print("="*60)
    print(stock_summary.sort_values('Total Profit (Rs)', ascending=False).to_string())

    print("\n" + "="*60)
    print("📅 MONTHLY PROFITABILITY TREND")
    print("="*60)
    print(monthly_summary.to_string())

    # 3. Overall Portfolio Metrics
    total_profit = trade_df['pnl_rs'].sum()
    print(f"\n🚀 OVERALL PORTFOLIO PROFIT: Rs {total_profit:.2f}")
    print(f"📈 AVERAGE PROFIT PER TRADE: Rs {trade_df['pnl_rs'].mean():.2f}")
    print(f"🎯 PORTFOLIO WIN RATE: {(trade_df['pnl_rs'] > 0).mean()*100:.1f}%")

if __name__ == "__main__":
    generate_detailed_report()
