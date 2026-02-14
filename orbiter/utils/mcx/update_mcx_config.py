#!/usr/bin/env python3
"""
🛠️ Utility: Update MCX Config
Scans common MCX commodities for current month Futures and updates config.py.
Extracts lot sizes directly from scrip search for maximum reliability.
"""
import sys
import os
import re
import time
import json

# Ensure we can import from project root (orbiter/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.client import BrokerClient
import config.main_config as config
import logging

# Common MCX symbols including Mini variations
MCX_SYMBOLS = [
    'CRUDEOIL', 'CRUDEOILM', 
    'NATURALGAS', 'NATURALGASM', 
    'GOLD', 'GOLDM', 'GOLDPETAL',
    'SILVER', 'SILVERM', 'SILVERMIC',
    'COPPER', 'ZINC', 'ZINCM',
    'LEAD', 'LEADM',
    'ALUMINIUM', 'ALUMINIUMM'
]

def main():
    print("🚀 Starting MCX Configuration Update...")
    
    # Initialize BrokerClient forced to MCX
    try:
        client = BrokerClient("../ShoonyaApi-py/cred.yml", segment_name='mcx')
    except Exception:
        client = BrokerClient(segment_name='mcx')
    
    if not client.login():
        print("❌ Login failed. Please check credentials/TOTP.")
        return

    print(f"📊 Scanning {len(MCX_SYMBOLS)} symbols for MCX Futures...")
    
    futures_list = []
    
    for symbol in MCX_SYMBOLS:
        # Resolve Future via searchscrip
        try:
            ret = client.api.searchscrip(exchange='MCX', searchtext=symbol)
            if ret and ret.get('stat') == 'Ok' and 'values' in ret:
                candidates = []
                import datetime
                today = datetime.date.today()
                for scrip in ret['values']:
                    # Look for FUTCOM only
                    if scrip.get('instname') == 'FUTCOM' and scrip.get('symname') == symbol:
                        exp_str = scrip.get('exp') or scrip.get('exd')
                        exp = client.master._parse_expiry_date(exp_str)
                        if exp and exp >= today:
                            candidates.append((exp, scrip['token'], scrip.get('tsym'), int(scrip.get('ls', 0))))
                
                if candidates:
                    candidates.sort(key=lambda x: x[0])
                    best = candidates[0]
                    fut_token = f"MCX|{best[1]}"
                    tsym = best[2]
                    lot_size = best[3]
                    
                    print(f"✅ {symbol:<15} -> {fut_token} ({tsym}) Lot: {lot_size}")
                    futures_list.append((symbol, fut_token, tsym, lot_size))
                else:
                    if config.VERBOSE_LOGS:
                        print(f"❌ {symbol:<15} -> NO CANDIDATES FOUND")
        except Exception as e:
            print(f"⚠️ Error scanning {symbol}: {e}")
            
        time.sleep(0.1)

    if not futures_list:
        print("❌ No MCX futures found. Exiting.")
        return

    # ✅ Save MCX Futures mapping [BaseSym, TSym, LotSize]
    mcx_map = {tok.split("|")[-1]: [sym, tsym, lot] for sym, tok, tsym, lot in futures_list}
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    map_path = os.path.join(base_dir, 'data', 'mcx_futures_map.json')
    
    with open(map_path, 'w') as f:
        json.dump(mcx_map, f, indent=4)
    print(f"💾 Saved MCX Futures mapping to {map_path}")

    # Update config/mcx/exchange_config.py
    config_path = os.path.join(base_dir, 'config', 'mcx', 'exchange_config.py')
    
    new_config_lines = ["SYMBOLS_FUTURE_UNIVERSE = ["]
    for sym, tok, tsym, lot in futures_list:
        new_config_lines.append(f"    '{tok}',  # {sym}")
    new_config_lines.append("]")
    new_config_str = "\n".join(new_config_lines)

    with open(config_path, 'r') as f:
        content = f.read()

    pattern = r"SYMBOLS_FUTURE_UNIVERSE\s*=\s*\[.*?\]"
    if re.search(pattern, content, re.DOTALL):
        new_content = re.sub(pattern, new_config_str, content, flags=re.DOTALL)
    else:
        new_content = content + "\n\n" + new_config_str + "\n"

    with open(config_path, 'w') as f:
        f.write(new_content)

    print(f"🎉 Config updated successfully: {config_path}")
    print(f"✅ Added {len(futures_list)} MCX future tokens.")

if __name__ == "__main__":
    main()
