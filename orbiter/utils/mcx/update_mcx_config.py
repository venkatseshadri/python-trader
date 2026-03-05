#!/usr/bin/env python3
"""
🛠️ Utility: Update MCX Config
Scans common MCX commodities for current month Futures and updates mcx_futures_map.json

Usage:
    python -m orbiter.utils.mcx.update_mcx_config

Or to download full MCX symbols from Shoonya:
    python -m orbiter.utils.mcx.update_mcx_config --full
"""
import sys
import os
import time
import json
import argparse
import zipfile
import io
import requests

# Ensure we can import from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from orbiter.core.broker import BrokerClient
from datetime import datetime, date

# Common MCX symbols including Minis and Micros
SYMBOLS = [
    'CRUDEOIL', 'CRUDEOILM', 
    'NATURALGAS', 
    'GOLD', 'GOLDM', 'GOLDPETAL', 'GOLDGUINEA', 'GOLDTEN',
    'SILVER', 'SILVERM', 'SILVERMIC',
    'COPPER', 
    'ZINC', 'ZINCMINI', 
    'LEAD', 'LEADMINI', 
    'ALUMINIUM',
    'NICKEL'
]

MCX_ROOT_URL = 'https://api.shoonya.com/'

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
            exp_str = nearest.get('exd', '').replace('-', '').upper() if nearest.get('exd') else ''
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
            
        futures_map[tok] = [symbol, tsym, int(ls) if ls else 1, exp_str]
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


def download_full_mcx_symbols():
    """Download full MCX symbols from Shoonya API and extract all futures."""
    print("📥 Downloading full MCX symbols from Shoonya...")
    
    url = MCX_ROOT_URL + 'MCX_symbols.txt.zip'
    
    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            print(f"❌ Failed to download: {response.status_code}")
            return
            
        print(f"✅ Downloaded {len(response.content)} bytes")
        
        # Extract the zip file in memory
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            file_name = z.namelist()[0]
            with z.open(file_name) as f:
                content = f.read().decode('utf-8')
        
        print(f"📊 Parsing {len(content)} bytes of symbol data...")
        
        futures_map = {}
        today = date.today()
        
        for line in content.strip().split('\n'):
            # Skip header line
            if line.startswith('Exchange,'):
                continue
                
            # Format: Exchange,Token,LotSize,GNGD,Symbol,TradingSymbol,Expiry,Instrument,OptionType,StrikePrice,TickSize
            parts = line.split(',')
            if len(parts) < 8:
                continue
            
            # MCX,477176,10,0.1,GOLDTEN,GOLDTEN31MAR26,31-MAR-2026,FUTCOM,XX,0,1
            exchange = parts[0]
            token = parts[1]
            lotsize = parts[2]
            symbol = parts[4]
            tsym = parts[5]
            exd = parts[6]  # DD-MON-YYYY
            instname = parts[7]  # FUTCOM, OPTFUT, etc.
            
            # Only process MCX futures
            if exchange != 'MCX' or instname not in ('FUTCOM', 'FUTIDX'):
                continue
            
            # Parse expiry date
            try:
                exp_date = datetime.strptime(exd, "%d-%b-%Y").date()
                if exp_date < today:
                    continue  # Skip expired
            except:
                continue
            
            # If we already have this symbol with a nearer expiry, skip
            if symbol in futures_map:
                existing_exp = futures_map[symbol][3]
                try:
                    existing_date = datetime.strptime(existing_exp, "%d%b%y").date()
                    if exp_date > existing_date:
                        continue  # Keep the nearer one
                except:
                    pass
            
            exp_str = exp_date.strftime("%d%b%y")
            futures_map[symbol] = [symbol, tsym, int(lotsize) if lotsize else 1, exp_str]
        
        if not futures_map:
            print("❌ No valid MCX futures found in the download.")
            return
        
        # Save to mcx_futures_map.json
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
        
        if os.path.basename(project_root) == 'orbiter':
            potential_root = os.path.dirname(project_root)
            if os.path.exists(os.path.join(potential_root, 'ShoonyaApi-py')):
                project_root = potential_root
        
        map_path = os.path.join(project_root, 'orbiter', 'data', 'mcx_futures_map.json')
        
        with open(map_path, 'w') as f:
            json.dump(futures_map, f, indent=4)
        
        print(f"💾 Saved {len(futures_map)} MCX futures to {map_path}")
        print(f"✅ Symbols: {list(futures_map.keys())}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Update MCX Futures Config')
    parser.add_argument('--full', action='store_true', help='Download full MCX symbols from Shoonya API')
    args = parser.parse_args()
    
    if args.full:
        download_full_mcx_symbols()
    else:
        main()
