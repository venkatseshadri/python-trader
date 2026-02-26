#!/usr/bin/env python3
"""
🛠️ Utility: Update MCX Config
Scans common MCX commodities for current month Futures and updates mcx_futures_map.json
"""
import sys
import os
import time
import json

# Ensure we can import from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from orbiter.core.broker import BrokerClient
from datetime import datetime

# Common MCX symbols
SYMBOLS = ['CRUDEOIL', 'NATURALGAS', 'GOLD', 'SILVER', 'COPPER', 'ZINC', 'LEAD', 'ALUMINIUM', 'NICKEL']

def main():
    print("🚀 Starting MCX Configuration Update...")
    
    # detect project root - go up from orbiter/utils/mcx/
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
    
    # Check if we're on RPI (orbiter is inside python-trader)
    if os.path.basename(project_root) == 'orbiter':
        potential_root = os.path.dirname(project_root)
        if os.path.exists(os.path.join(potential_root, 'ShoonyaApi-py')):
            project_root = potential_root
    
    cred_path = os.path.join(project_root, 'ShoonyaApi-py', 'cred.yml')
    print(f"📂 Project Root: {project_root}")
    print(f"📂 Cred Path: {cred_path}")
    
    try:
        client = BrokerClient(project_root=project_root, 
                            config_path=cred_path,
                            segment_name='mcx')
    except Exception as e:
        print(f"❌ Failed to initialize BrokerClient: {e}")
        return
    
    # Ensure MCX master is loaded
    client.download_scrip_master('MCX')
    
    if not client.login():
        print("❌ Login failed. Please check credentials/TOTP.")
        return

    print(f"📊 Scanning {len(SYMBOLS)} symbols for MCX Futures...")
    
    futures_map = {}
    
    for symbol in SYMBOLS:
        # Use searchscrip to find futures for this symbol
        try:
            result = client.api.searchscrip(exchange='MCX', searchtext=symbol)
        except Exception as e:
            print(f"❌ {symbol:<15} -> Search failed: {e}")
            continue
            
        if not result or result.get('stat') != 'Ok':
            print(f"❌ {symbol:<15} -> Search failed: {result}")
            continue
        
        # Response is in result['values']
        results = result.get('values', [])
        
        # Filter for futures only (FUTCOM or FUTIDX), not options (OPTFUT)
        futures = [r for r in results if r.get('instname') in ('FUTCOM', 'FUTIDX')]
        
        if not futures:
            print(f"❌ {symbol:<15} -> NO FUTURES FOUND")
            continue
        
        # Sort by expiry - find the one with nearest expiry that's not expired
        today = datetime.now()
        
        valid_futures = []
        for f in futures:
            exp_str = f.get('exd', '')  # Format: 19-MAR-2026
            if exp_str:
                try:
                    exp_date = datetime.strptime(exp_str, "%d-%b-%Y")
                    if exp_date >= today:
                        valid_futures.append((f, exp_date))
                except:
                    pass
        
        if not valid_futures:
            # No valid futures found, just pick the first one
            nearest = futures[0]
            tok = nearest.get('token')
            tsym = nearest.get('tsym')
            ls = nearest.get('ls', 1)
            print(f"⚠️ {symbol:<15} -> {tok} ({tsym}) [Lot: {ls}] [EXPIRED?]")
        else:
            # Sort by expiry and get nearest
            valid_futures.sort(key=lambda x: x[1])
            nearest, exp_date = valid_futures[0]
            tok = nearest.get('token')
            tsym = nearest.get('tsym')
            ls = nearest.get('ls', 1)
            exp_str = exp_date.strftime("%d%b%y")
            print(f"✅ {symbol:<15} -> {tok} ({tsym}) [Lot: {ls}] [Expiry: {exp_str}]")
            
        futures_map[tok] = [symbol, tsym, int(ls) if ls else 1]
        time.sleep(0.2)

    if not futures_map:
        print("❌ No MCX futures found. Exiting.")
        return

    # Save to mcx_futures_map.json
    map_path = os.path.join(project_root, 'orbiter', 'data', 'mcx_futures_map.json')
    
    with open(map_path, 'w') as f:
        json.dump(futures_map, f, indent=4)
    
    print(f"💾 Saved MCX Futures mapping to {map_path}")
    print(f"✅ Added {len(futures_map)} MCX future tokens.")

if __name__ == "__main__":
    main()
