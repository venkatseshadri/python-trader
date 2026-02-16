import argparse
import pandas as pd
import os
import sys
from datetime import datetime, time as dt_time
import talib

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from backtest_lab.core.loader import DataLoader
from backtest_lab.core.pdf_generator import create_orbitron_report
from backtest_lab.core.excel_generator import create_excel_report
from backtest_lab.core.reporter import calculate_advanced_stats

# Shared logic from previous iterations
from backtest_lab.generate_unified_matrix import UnifiedFastExitEngine, resample_data

class BacktestEngine:
    def __init__(self, scrips, start_date, end_date):
        self.scrips = scrips
        self.start_date = pd.to_datetime(start_date).date()
        self.end_date = pd.to_datetime(end_date).date()
        self.trades = []
        # Basic Lot mapping
        self.lot_sizes = {"RELIANCE": 250, "TCS": 175, "LT": 175, "SBIN": 750, "HDFCBANK": 550, "ICICIBANK": 700, "AXISBANK": 625, "KOTAKBANK": 400, "BOSCHLTD": 25}

    def run(self):
        print(f"🚀 Starting Backtest for {self.scrips}")
        print(f"📅 Period: {self.start_date} to {self.end_date}")
        
        for stock in self.scrips:
            self._process_stock(stock)
            
        return pd.DataFrame(self.trades)

    def _process_stock(self, stock):
        csv_path = f"backtest_lab/data/stocks/{stock}_minute.csv"
        if not os.path.exists(csv_path):
            print(f"⚠️ Data not found for {stock}: {csv_path}")
            return

        loader = DataLoader(csv_path)
        df = loader.load_data(days=365) 
        df['date'] = pd.to_datetime(df['date'])
        
        # Indicators
        df_5m = df.set_index('date').resample('5min').agg({'close':'last'}).dropna()
        df_5m['ema9_5m'] = talib.EMA(df_5m['close'].values.astype(float), 9)
        
        df_15m = df.set_index('date').resample('15min').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
        df_15m['ema5'] = talib.EMA(df_15m['close'].values.astype(float), 5)
        df_15m['ema9'] = talib.EMA(df_15m['close'].values.astype(float), 9)
        df_15m['ema20'] = talib.EMA(df_15m['close'].values.astype(float), 20)
        df_15m['ema50'] = talib.EMA(df_15m['close'].values.astype(float), 50)
        df_15m['adx'] = talib.ADX(df_15m['high'], df_15m['low'], df_15m['close'], 14)
        
        # Merge back to 1m
        df = df.merge(df_5m[['ema9_5m']], on='date', how='left').ffill()
        df = df.merge(df_15m[['ema5','ema9','ema20','ema50','adx']], on='date', how='left').ffill()
        
        # Trim to timeframe
        df = df[(df['date'].dt.date >= self.start_date) & (df['date'].dt.date <= self.end_date)].reset_index(drop=True)
        
        in_position = False
        entry_price = 0
        max_pnl = 0
        lot = self.lot_sizes.get(stock, 50)
        current_date = None
        orb_l = 0
        
        for i, row in df.iterrows():
            t = row['date'].time()
            d = row['date'].date()
            
            if d != current_date:
                current_date = d
                day_data = df[df['date'].dt.date == d]
                orb_mask = (day_data['date'].dt.time >= dt_time(9,15)) & (day_data['date'].dt.time <= dt_time(10,0))
                if orb_mask.any():
                    orb_l = day_data.loc[orb_mask, 'low'].min()
                else: orb_l = 0
            
            if not in_position:
                if t.minute % 15 == 0 and t >= dt_time(10, 15) and t <= dt_time(14, 30):
                    is_short = (row['ema5'] < row['ema9']) and (row['ema20'] < row['ema50']) and (row['adx'] > 25)
                    if is_short and row['close'] < orb_l:
                        in_position = True
                        entry_price = row['close']
                        self.trades.append({'Time': row['date'], 'Stock': stock, 'Action': 'ENTRY (SHORT)', 'Price': entry_price, 'PnL_Rs': 0, 'Reason': 'Elite_Short'})
                        max_pnl = 0
            else:
                pnl = (entry_price - row['close']) * lot
                max_pnl = max(max_pnl, pnl)
                exit_hit = row['close'] > row['ema9_5m'] or (max_pnl > 1000 and pnl < (max_pnl * 0.70)) or t >= dt_time(15, 15)
                if exit_hit:
                    self.trades.append({'Time': row['date'], 'Stock': stock, 'Action': 'SQUARE-OFF', 'Price': row['close'], 'PnL_Rs': round(pnl, 2), 'Reason': 'FAST_EXIT'})
                    in_position = False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Institutional Sniper Standardized Backtest")
    parser.add_argument('--stocks', nargs='+', required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--output', default='backtest_results')
    args = parser.parse_args()
    
    runner = BacktestEngine(args.stocks, args.start, args.end)
    results_df = runner.run()
    
    if not results_df.empty:
        os.makedirs(args.output, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 🛡️ ORBITRON HIGH FIDELITY
        capital = 100000 # Could be parameterized in future
        full_data = calculate_advanced_stats(results_df, capital=capital)
        full_data['Capital'] = capital
        
        strategy_meta = {
            "Backtest ID": f"BT_{timestamp}",
            "Strategy": f"Institutional Sniper - {', '.join(args.stocks)}",
            "Link": "https://github.com/vseshadri/python-trader",
            "Period": f"{args.start} to {args.end}",
            "Frequency": "1 Minute | Multi-TF Filter",
            "Notes": "Automated Backtest Run for Strategy Refinement."
        }
        
        create_orbitron_report(full_data, os.path.join(args.output, f"Orbitron_Report_{timestamp}.pdf"), strategy_meta=strategy_meta)
        
        create_excel_report(results_df, os.path.join(args.output, f"Orbitron_Trades_{timestamp}.xlsx"))
        print("\n✅ Orbitron Professional Backtest Complete.")
    else:
        print("\n⚠️ No trades generated.")
