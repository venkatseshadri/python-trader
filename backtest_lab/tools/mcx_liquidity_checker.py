import sys
import os
import json
from datetime import datetime

# Add paths for Shoonya and Orbiter
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(project_root, 'orbiter'))
sys.path.append(os.path.join(project_root, 'ShoonyaApi-py'))

from core.broker import BrokerClient
from core.broker.master import ScripMaster

def check_mcx_liquidity():
    print(f"🔍 Analyzing MCX Option Liquidity @ {datetime.now().strftime('%H:%M:%S')}...")
    
    # Use standard cred path and specify MCX segment
    client = BrokerClient(config_path='ShoonyaApi-py/cred.yml', segment_name='mcx')
    if not client.login():
        print("❌ Authentication failed.")
        return

    # Metals to check
    metals = ['GOLD', 'GOLDM', 'SILVER', 'SILVERM', 'COPPER', 'ZINC', 'ALUMINIUM']
    
    # 1. Get near futures to find ATM strikes
    results = []
    
    for symbol in metals:
        print(f"📊 Checking {symbol}...")
        fut = client.resolver.get_near_future(symbol, 'MCX', client.api)
        if not fut:
            print(f"  ⚠️ Could not find future for {symbol}")
            continue
            
        quote = client.api.get_quotes(exchange='MCX', token=fut['token'].split('|')[1])
        if not quote or 'lp' not in quote:
            print(f"  ⚠️ Could not get LTP for {fut['tsym']}")
            continue
            
        ltp = float(quote['lp'])
        
        # 2. Find ATM Option
        # Get options for this symbol
        options = [r for r in client.master.DERIVATIVE_OPTIONS if r.get('symbol') == symbol and r.get('instrument') == 'OPTFUT']
        if not options:
            print(f"  ⚠️ No options found for {symbol} in master.")
            continue
            
        # Get unique strikes
        strikes = sorted(list(set([float(o['strike']) for o in options if o.get('strike')])))
        atm_strike = min(strikes, key=lambda s: abs(s - ltp))
        
        # Get ATM Call and Put tokens
        atm_options = [o for o in options if float(o.get('strike', 0)) == atm_strike]
        
        for opt in atm_options:
            token = opt['token']
            tsym = opt['tradingsymbol']
            
            # Fetch depth for liquidity analysis
            depth = client.api.get_quotes(exchange='MCX', token=token)
            if not depth: continue
            
            bid = float(depth.get('bp1', 0))
            ask = float(depth.get('sp1', 0))
            vol = int(depth.get('v', 0))
            oi = int(depth.get('oi', 0))
            
            spread = ask - bid
            spread_pct = (spread / bid * 100) if bid > 0 else 0
            
            results.append({
                'symbol': tsym,
                'ltp': float(depth.get('lp', 0)),
                'bid': bid,
                'ask': ask,
                'spread_pct': spread_pct,
                'volume': vol,
                'oi': oi
            })

    print(f"\n{'Option':<20} | {'LTP':<8} | {'Spread%':<8} | {'Volume':<8} | {'OI':<8}")
    print("-" * 65)
    for res in sorted(results, key=lambda x: x['volume'], reverse=True):
        status = "✅ LIQUID" if res['spread_pct'] < 0.5 and res['volume'] > 100 else "❌ ILLIQUID"
        print(f"{res['symbol']:<20} | {res['ltp']:<8.2f} | {res['spread_pct']:<8.2f}% | {res['volume']:<8} | {res['oi']:<8} | {status}")

if __name__ == "__main__":
    check_mcx_liquidity()
