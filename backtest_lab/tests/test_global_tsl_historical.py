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
    # 1. Load Data
    symbol = "ADANIENT"
    csv_path = f"backtest_lab/data/stocks/{symbol}_minute.csv"
    if not os.path.exists(csv_path):
        print(f"❌ Data file not found: {csv_path}")
        return

    loader = DataLoader(csv_path)
    df = loader.load_data(days=60) # Last 60 days
    
    # 2. Setup Engine
    mock_client = MagicMock()
    mock_client.SYMBOLDICT = {}
    mock_client.get_ltp = lambda token: mock_client.SYMBOLDICT.get(token, {}).get('ltp', 0)
    
    config = {
        'TOP_N': 5,
        'TRADE_SCORE': 0.5,
        'TOTAL_TARGET_PROFIT_RS': 2000, # Target 2k
        'TOTAL_STOP_LOSS_RS': 0,
        'GLOBAL_TSL_ENABLED': True,
        'GLOBAL_TSL_PCT': 20.0, # 20% retracement
        'VERBOSE_LOGS': False, # Reduce noise
        'OPTION_EXECUTE': False,
        'OPTION_PRODUCT_TYPE': 'I'
    }
    
    # 3. Simulate Day-by-Day
    # Group by date
    days = df.groupby(df['date'].dt.date)
    
    print(f"🧪 Testing Global TSL on {symbol} (Target: ₹2000, TSL: 20%)")
    
    for date, day_df in days:
        # Reset State for the day
        state = OrbiterState(mock_client, [], [], config)
        state.active_positions = {}
        state.max_portfolio_pnl = 0.0
        state.global_tsl_active = False
        executor = Executor(MagicMock(), MagicMock(), [], [])
        
        # Simulate Entry at 9:30 AM
        entry_row = day_df[day_df['date'].dt.time >= datetime.strptime("09:30", "%H:%M").time()].iloc[0]
        entry_price = entry_row['close']
        entry_time = entry_row['date']
        
        token = f"NSE|{symbol}"
        state.active_positions[token] = {
            'entry_price': entry_price,
            'entry_time': entry_time,
            'symbol': symbol,
            'strategy': 'FUTURE_LONG',
            'lot_size': 50, # 1 Lot of Adani Ent ~ 50 qty (older data might differ, assume 50)
            'tsl_activation_rs': 100000, # Disable per-trade TSL to isolate Global TSL
            'max_pnl_rs': 0
        }
        
        tsl_triggered = False
        peak_pnl = 0
        exit_pnl = 0
        
        # Stream Candles
        for idx, row in day_df.iterrows():
            if row['date'] <= entry_time: continue
            
            ltp = row['close']
            mock_client.SYMBOLDICT[token] = {'ltp': ltp}
            
            # Run Check
            # We must verify if check_sl returns anything
            # But check_sl calls square_off_all if mass exit
            # So we mock square_off_all to capture the event
            executor.square_off_all = MagicMock(return_value=[{'reason': 'Global TSL Hit'}])
            
            # Calculate current PnL for logging
            pnl = (ltp - entry_price) * 50
            peak_pnl = max(peak_pnl, pnl)
            
            # Only log if PnL is positive significant
            # if pnl > 1000: print(f"  {row['date'].time()} PnL: {pnl:.0f}")

            # Execute Logic
            res = executor.check_sl(state, MagicMock())
            
            # Check if square_off_all was called
            if executor.square_off_all.called:
                args, kwargs = executor.square_off_all.call_args
                reason = kwargs.get('reason', '')
                if "Global TSL Hit" in reason:
                    print(f"✅ {date}: Global TSL HIT! Peak PnL: ₹{peak_pnl:.0f} -> Exit PnL: ₹{pnl:.0f} ({reason})")
                    tsl_triggered = True
                    break
        
        if not tsl_triggered and peak_pnl > 2000:
             print(f"❌ {date}: Failed to trigger! Peak PnL: ₹{peak_pnl:.0f} (Target 2000)")
        elif tsl_triggered:
             pass # Already printed
        else:
             # Day didn't reach target
             pass 

if __name__ == "__main__":
    run_historical_test()
