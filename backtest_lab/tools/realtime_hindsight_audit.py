import sys
import os
import json
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np
import talib

# Path setup for Pi execution
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(project_root, 'orbiter'))
sys.path.append(os.path.join(project_root, 'ShoonyaApi-py'))

from core.broker import BrokerClient
from core.broker.master import ScripMaster

def audit_realtime():
    print(f"🕵️  Real-time Hindsight Audit (5:00 PM - Now) @ {datetime.now().strftime('%H:%M:%S')}...")
    
    client = BrokerClient(config_path='ShoonyaApi-py/cred.yml', segment_name='mcx')
    if not client.login():
        print("❌ Authentication failed.")
        return

    # Metals to check
    metals = ['GOLD', 'SILVER', 'CRUDEOIL']
    ist = pytz.timezone('Asia/Kolkata')
    
    # 5:00 PM IST today
    start_dt = datetime.now(ist).replace(hour=17, minute=0, second=0, microsecond=0)
    end_dt = datetime.now(ist)
    
    data_map = {}
    
    for symbol in metals:
        print(f"📊 Fetching {symbol} data...")
        fut = client.resolver.get_near_future(symbol, 'MCX', client.api)
        if not fut: continue
        
        ex, tk = fut['token'].split('|')
        res = client.api.get_time_price_series(exchange=ex, token=tk, 
                                             starttime=int(start_dt.timestamp()), 
                                             endtime=int(end_dt.timestamp()), 
                                             interval=1)
        if res and isinstance(res, list):
            df = pd.DataFrame(res)
            df['intc'] = pd.to_numeric(df['intc'])
            df['inth'] = pd.to_numeric(df['inth'])
            df['intl'] = pd.to_numeric(df['intl'])
            data_map[symbol] = df
            print(f"  ✅ Received {len(df)} candles for {symbol}")

    if len(data_map) < 2:
        print("❌ Not enough data for pair analysis.")
        return

    # 1. Ratio Audit (Gold vs Silver)
    if 'GOLD' in data_map and 'SILVER' in data_map:
        print("
📈 AUDIT: GOLD/SILVER RATIO")
        combined = pd.DataFrame({
            'GC': data_map['GOLD']['intc'],
            'SI': data_map['SILVER']['intc']
        }).ffill().dropna()
        
        combined['ratio'] = combined['GC'] / combined['SI']
        combined['mean'] = combined['ratio'].rolling(60).mean()
        combined['std'] = combined['ratio'].rolling(60).std()
        combined['zscore'] = (combined['ratio'] - combined['mean']) / combined['std']
        
        signals = combined[abs(combined['zscore']) > 2.0]
        if signals.empty:
            print("  ➖ No Ratio triggers found (Market was stable).")
        else:
            for ts, row in signals.iterrows():
                # Get actual time from data_map
                time_str = data_map['GOLD'].iloc[ts]['time']
                print(f"  🔥 SIGNAL @ {time_str} | Z-Score: {row['zscore']:.2f}")

    # 2. Solo Reversion (Crude Oil)
    if 'CRUDEOIL' in data_map:
        print("
🛢️  AUDIT: CRUDE OIL MEAN REVERSION")
        df = data_map['CRUDEOIL']
        upper, middle, lower = talib.BBANDS(df['intc'], timeperiod=20, nbdevup=2, nbdevdn=2)
        
        for i in range(len(df)):
            ltp = df['intc'].iloc[i]
            if ltp < lower.iloc[i]:
                print(f"  🟢 BUY CL @ {df['time'].iloc[i]} (Price: {ltp} < Lower: {lower.iloc[i]:.2f})")
            elif ltp > upper.iloc[i]:
                print(f"  🔴 SELL CL @ {df['time'].iloc[i]} (Price: {ltp} > Upper: {upper.iloc[i]:.2f})")

if __name__ == "__main__":
    audit_realtime()
