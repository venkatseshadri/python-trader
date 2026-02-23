import sys
import os
import pandas as pd
from unittest.mock import MagicMock
from datetime import datetime, timedelta

# Fix paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from orbiter.core.engine.executor import Executor
from orbiter.core.engine.state import OrbiterState
from backtest_lab.core.loader import DataLoader

def run_historical_test():
    # 1. Configuration Matrix
    targets = [2000, 5000, 10000]
    tsl_pcts = [20, 25, 50]
    
    symbols = [
        "HDFCBANK", "RELIANCE", "ICICIBANK", "INFY", "TCS", 
        "ITC", "LT", "AXISBANK", "BHARTIARTL", "SBIN"
    ]
    
    # Pre-load data to optimize speed
    print(f"⏳ Pre-loading data for {len(symbols)} stocks...")
    stock_data = {}
    for symbol in symbols:
        csv_path = f"backtest_lab/data/stocks/{symbol}_minute.csv"
        if os.path.exists(csv_path):
            loader = DataLoader(csv_path)
            df = loader.load_data(days=60)
            stock_data[symbol] = df
        else:
            print(f"❌ Missing: {symbol}")

    print("\n" + "="*80)
    print(f"🧪 GLOBAL TSL MATRIX SIMULATION (Top 10 NIFTY Stocks | 60 Days)")
    print("="*80)
    print(f"{'Target (₹)':<12} | {'TSL %':<8} | {'Net Benefit':<15} | {'Extra Profit':<15} | {'Give Back':<15} | {'Win Rate':<10}")
    print("-" * 80)

    results = []

    # 2. Run Combinations
    for target in targets:
        for tsl_pct in tsl_pcts:
            
            combo_extra = 0
            combo_give_back = 0
            wins = 0
            losses = 0
            
            # Setup State
            mock_client = MagicMock()
            mock_client.SYMBOLDICT = {}
            mock_client.get_ltp = lambda token: mock_client.SYMBOLDICT.get(token, {}).get('ltp', 0)
            
            config = {
                'TOP_N': 5,
                'TRADE_SCORE': 0.5,
                'TOTAL_TARGET_PROFIT_RS': target,
                'TOTAL_STOP_LOSS_RS': 0,
                'GLOBAL_TSL_ENABLED': True,
                'GLOBAL_TSL_PCT': float(tsl_pct),
                'VERBOSE_LOGS': False,
                'OPTION_EXECUTE': False,
                'OPTION_PRODUCT_TYPE': 'I'
            }

            for symbol, df in stock_data.items():
                days = df.groupby(df['date'].dt.date)
                
                # Realistic Lot Sizes
                lot_map = {
                    'HDFCBANK': 550, 'RELIANCE': 250, 'ICICIBANK': 700, 'INFY': 400, 'TCS': 175,
                    'ITC': 1600, 'LT': 175, 'AXISBANK': 625, 'BHARTIARTL': 950, 'SBIN': 1500
                }
                lot_size = lot_map.get(symbol, 50)

                for date, day_df in days:
                    state = OrbiterState(mock_client, [], [], config)
                    state.active_positions = {}
                    state.max_portfolio_pnl = 0.0
                    state.global_tsl_active = False
                    executor = Executor(MagicMock(), MagicMock(), [], [])
                    
                    # Entry Logic (9:30 AM)
                    entry_mask = day_df['date'].dt.time >= datetime.strptime("09:30", "%H:%M").time()
                    if not entry_mask.any(): continue
                    entry_row = day_df[entry_mask].iloc[0]
                    entry_price = entry_row['close']
                    entry_time = entry_row['date']
                    
                    token = f"NSE|{symbol}"
                    state.active_positions[token] = {
                        'entry_price': entry_price, 'entry_time': entry_time,
                        'symbol': symbol, 'strategy': 'FUTURE_LONG',
                        'lot_size': lot_size, 'tsl_activation_rs': 100000, 'max_pnl_rs': 0
                    }
                    
                    peak_pnl = 0
                    triggered = False
                    
                    # Sim Loop
                    for idx, row in day_df.iterrows():
                        if row['date'] <= entry_time: continue
                        ltp = row['close']
                        mock_client.SYMBOLDICT[token] = {'ltp': ltp}
                        
                        pnl = (ltp - entry_price) * lot_size
                        peak_pnl = max(peak_pnl, pnl)
                        
                        # Mock Exit Trigger
                        executor.square_off_all = MagicMock(return_value=[{'reason': 'Global TSL Hit'}])
                        executor.check_sl(state, MagicMock())
                        
                        if executor.square_off_all.called:
                            args, kwargs = executor.square_off_all.call_args
                            reason = kwargs.get('reason', '')
                            if "Global TSL Hit" in reason:
                                diff = pnl - target
                                if diff >= 0:
                                    combo_extra += diff
                                    wins += 1
                                else:
                                    combo_give_back += abs(diff)
                                    losses += 1
                                triggered = True
                                break
                    
                    # If target reached but TSL never triggered (e.g. EOD exit above target)
                    # For fairness, we assume EOD exit at close
                    if not triggered and peak_pnl >= target:
                        # If peak >= target, TSL activated. 
                        # If we reached EOD without hitting floor, we exit at Close.
                        # Check close price
                        close_price = day_df.iloc[-1]['close']
                        final_pnl = (close_price - entry_price) * lot_size
                        
                        # Calculate floor based on peak
                        allowed_drop = peak_pnl * (tsl_pct / 100.0)
                        floor = peak_pnl - allowed_drop
                        
                        if final_pnl > floor:
                            # We exit at EOD with profit > floor
                            diff = final_pnl - target
                            if diff >= 0:
                                combo_extra += diff
                                wins += 1
                            else:
                                combo_give_back += abs(diff)
                                losses += 1
                        else:
                            # Technically should have exited earlier, but simple simulation logic handles trigger check
                            pass

            net_benefit = combo_extra - combo_give_back
            win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
            
            print(f"₹{target:<11} | {tsl_pct:<8}% | ₹{net_benefit:<14.0f} | ₹{combo_extra:<14.0f} | ₹{combo_give_back:<14.0f} | {win_rate:.1f}%")
            results.append((target, tsl_pct, net_benefit))

    print("-" * 80)
    best = max(results, key=lambda x: x[2])
    print(f"🏆 BEST CONFIG: Target ₹{best[0]} with {best[1]}% TSL (Net Benefit: ₹{best[2]:.0f})")
    print("-" * 80)

if __name__ == "__main__":
    run_historical_test()
