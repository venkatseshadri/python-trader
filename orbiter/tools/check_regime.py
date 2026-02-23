import sys
import os
import talib
import numpy as np
import pandas as pd
from datetime import datetime

# Path setup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from orbiter.core.broker import BrokerClient

def check_market_regime():
    print(f"🕵️ Analyzing Market Regime @ {datetime.now().strftime('%H:%M:%S')}...")
    
    try:
        # 1. Connect
        client = BrokerClient('../ShoonyaApi-py/cred.yml', segment_name='nfo')
        client.login()
        
        # 2. Targets: Nifty Index + Top Volatile Stocks
        # Nifty 50 Token (need to resolve or use hardcoded if known, but search is safer)
        # We'll use Top Stocks for proxy if Index token is tricky to find dynamically
        symbols = ['NIFTY 50', 'RELIANCE', 'HDFCBANK', 'ADANIENT', 'WIPRO']
        
        results = []
        
        print(f"{'Symbol':<15} | {'ADX(14)':<8} | {'Regime':<12} | {'BB Width':<8}")
        print("-" * 55)
        
        for sym in symbols:
            # Resolve Token
            token = client.get_token(sym)
            if not token: 
                # Try Futures?
                fut = client.get_near_future(sym)
                if fut: token = fut['token']
            
            if not token: continue
            
            # Fetch History (last 60 mins)
            # Exchange: NSE for Index/Stock, NFO for Futures
            # Try NSE first
            exch = 'NSE'
            if sym == 'NIFTY 50': token = '26000' # Common Nifty Token ID
            
            # Fetch 100 candles
            end = int(datetime.now().timestamp())
            start = end - (100 * 60)
            
            # Try NSE
            candles = client.api.get_time_price_series(exchange='NSE', token=token, starttime=start, endtime=end, interval=1)
            if not candles:
                # Try NFO Future
                fut = client.get_near_future(sym)
                if fut:
                    token = fut['token']
                    candles = client.api.get_time_price_series(exchange='NFO', token=token, starttime=start, endtime=end, interval=1)
            
            if not candles: continue
            
            # Process
            closes = np.array([float(c['intc']) for c in candles])
            highs = np.array([float(c['inth']) for c in candles])
            lows = np.array([float(c['intl']) for c in candles])
            
            if len(closes) < 20: continue
            
            # Indicators
            adx = talib.ADX(highs, lows, closes, timeperiod=14)[-1]
            up, mid, low = talib.BBANDS(closes, timeperiod=20)
            bb_width = ((up[-1] - low[-1]) / mid[-1]) * 100
            
            regime = "TRENDING 🚀" if adx > 25 else "SIDEWAYS 🦀"
            
            print(f"{sym:<15} | {adx:<8.2f} | {regime:<12} | {bb_width:<8.2f}%")
            results.append({'sym': sym, 'adx': adx, 'regime': regime})

        # Summary
        avg_adx = np.mean([r['adx'] for r in results])
        print("-" * 55)
        print(f"📊 Market Average ADX: {avg_adx:.2f}")
        if avg_adx < 20:
            print("💡 STRATEGY: Market is DEAD. 'Range Raider' is ideal.")
        elif avg_adx > 30:
            print("💡 STRATEGY: Market is HOT. 'Orbital' (Breakout) is ideal.")
        else:
            print("💡 STRATEGY: Mixed/Choppy. Be cautious.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_market_regime()
