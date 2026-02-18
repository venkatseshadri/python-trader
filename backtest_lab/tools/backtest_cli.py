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
    def __init__(self, scrips, start_date, end_date, scenario_path=None):
        self.scrips = scrips
        self.start_date = pd.to_datetime(start_date).date()
        self.end_date = pd.to_datetime(end_date).date()
        self.trades = []
        self.scenario = None
        if scenario_path:
            import json
            full_path = os.path.join('backtest_lab/scenarios', scenario_path)
            if os.path.exists(full_path):
                with open(full_path) as f:
                    self.scenario = json.load(f)
                    print(f"✅ Loaded Scenario: {self.scenario.get('name')}")
        
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
        df['ema9_1m'] = talib.EMA(df['close'].values.astype(float), 9)
        df['ema20_1m'] = talib.EMA(df['close'].values.astype(float), 20)
        
        # Calculate 1m Wick Stats for exit logic
        df['tr'] = (df['high'] - df['low']).replace(0, 1e-9)
        df['l_wick_pct'] = (df[['open', 'close']].min(axis=1) - df['low']) / df['tr']
        df['u_wick_pct'] = (df['high'] - df[['open', 'close']].max(axis=1)) / df['tr']

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
        
        # New Ribbon Calculation for ef6
        df['ribbon_gap'] = abs(df['ema5'] - df['ema9']) / df['ema5'] * 100

        # Trim to timeframe
        df = df[(df['date'].dt.date >= self.start_date) & (df['date'].dt.date <= self.end_date)].reset_index(drop=True)
        
        in_position = False
        entry_price = 0
        max_pnl = 0
        lot = self.lot_sizes.get(stock, 50)
        current_date = None
        last_trade_date = None 
        orb_l = 0
        yest_high = 0
        yest_low = 0
        
        for i, row in df.iterrows():
            t = row['date'].time()
            d = row['date'].date()
            
            if d != current_date:
                current_date = d
                day_data = df[df['date'].dt.date == d]
                prev_day_data = df[df['date'].dt.date < d].tail(375)
                if not prev_day_data.empty:
                    yest_high = prev_day_data['high'].max()
                    yest_low = prev_day_data['low'].min()
                
                orb_mask = (day_data['date'].dt.time >= dt_time(9,15)) & (day_data['date'].dt.time <= dt_time(10,0))
                if orb_mask.any():
                    orb_l = day_data.loc[orb_mask, 'low'].min()
                else: orb_l = 0
            
            if not in_position:
                if d != last_trade_date:
                    score = 0.0
                    if self.scenario:
                        if row['adx'] > 25: score += 0.25 
                        if row['ribbon_gap'] < 0.05: score += 0.25 
                        if row['close'] < yest_low: score += 0.50 
                        
                        threshold = self.scenario.get('TRADE_SCORE', 1.0)
                        if score >= threshold and t >= dt_time(10, 15) and t <= dt_time(13, 00):
                            in_position = True
                            last_trade_date = d
                            entry_price = row['close']
                            max_pnl = 0
                            self.trades.append({'Time': row['date'], 'Stock': stock, 'Action': 'ENTRY (SHORT)', 'Price': entry_price, 'PnL_Rs': 0, 'Reason': 'Pattern_Alpha'})
                    else:
                        if t.minute % 15 == 0 and t >= dt_time(10, 15) and t <= dt_time(14, 30):
                            is_short = (row['ema5'] < row['ema9']) and (row['ema20'] < row['ema50']) and (row['adx'] > 25)
                            if is_short and row['close'] < orb_l:
                                in_position = True
                                last_trade_date = d
                                entry_price = row['close']
                                max_pnl = 0
                                self.trades.append({'Time': row['date'], 'Stock': stock, 'Action': 'ENTRY (SHORT)', 'Price': entry_price, 'PnL_Rs': 0, 'Reason': 'Elite_Short'})
            else:
                pnl = (entry_price - row['close']) * lot
                max_pnl = max(max_pnl, pnl)
                
                # 1. Hard SL (0.5%)
                hard_sl = entry_price * 1.005
                
                # 2. Dynamic Trailing SL
                trailing_exit = False
                if max_pnl > 2000:
                    trailing_exit = pnl < (max_pnl * 0.85) # Keep 85%
                elif max_pnl > 1000:
                    trailing_exit = pnl < (max_pnl * 0.70) # Keep 70%
                
                # 3. Wick Reversal Check (3 consecutive lower wicks > 40%)
                wick_reversal = False
                if i > 2:
                    prev_wicks = df.loc[i-2:i, 'l_wick_pct'].mean()
                    if prev_wicks > 0.40: wick_reversal = True

                exit_hit = (row['close'] > hard_sl) or \
                           (row['close'] > row['ema20_1m']) or \
                           trailing_exit or \
                           wick_reversal or \
                           (t >= dt_time(15, 15))
                
                if exit_hit:
                    reason = "HARD_SL" if row['close'] > hard_sl else ("EMA_EXIT" if row['close'] > row['ema20_1m'] else ("WICK_REV" if wick_reversal else "TSL"))
                    if t >= dt_time(15, 15): reason = "EOD"
                    self.trades.append({'Time': row['date'], 'Stock': stock, 'Action': 'SQUARE-OFF', 'Price': row['close'], 'PnL_Rs': round(pnl, 2), 'Reason': reason})
                    in_position = False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Institutional Sniper Standardized Backtest")
    parser.add_argument('--stocks', nargs='+', required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--scenario', default=None)
    parser.add_argument('--output', default='backtest_results')
    args = parser.parse_args()
    
    runner = BacktestEngine(args.stocks, args.start, args.end, scenario_path=args.scenario)
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
