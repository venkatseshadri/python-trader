#!/usr/bin/env python3
"""
🛠️ Utility: Update MCX Config
Scans common MCX commodities for current month Futures and updates config.py
"""
import sys
import os
import re
import time

# Ensure we can import from project root (orbiter/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from orbiter.core.broker import BrokerClient
import orbiter.config.config as config
import logging

# Common MCX symbols
import orbiter.config.mcx.config as mcx_config

def main():
    print("🚀 Starting MCX Configuration Update...")
    
    # Initialize BrokerClient
    try:
        client = BrokerClient("../ShoonyaApi-py/cred.yml", segment_name='mcx')
    except Exception:
        client = BrokerClient(segment_name='mcx')
    
    # Ensure MCX master is loaded for Lot Sizes
    client.download_scrip_master('MCX')
    
    if not client.login():
        print("❌ Login failed. Please check credentials/TOTP.")
        return

    print(f"📊 Scanning {len(mcx_config.SYMBOLS_UNIVERSE)} symbols for MCX Futures...")
    
    futures_list = []
    
    for symbol in mcx_config.SYMBOLS_UNIVERSE:
        res = client.get_near_future(symbol, exchange='MCX')
        fut_token = res['token'] if res else None
        tsym = res['tsym'] if res else None
        
        # 🔥 Extract Lot Size from Master
        ls = 0
        if tsym:
            # Check Derivative Master in Client
            for r in client.master.DERIVATIVE_OPTIONS:
                if r.get('tradingsymbol') == tsym:
                    ls = int(r.get('lot_size', 0))
                    break
        
        if fut_token:
            print(f"✅ {symbol:<15} -> {fut_token} ({tsym}) [Lot: {ls}]")
            futures_list.append((symbol, fut_token, tsym, ls))
        else:
            print(f"❌ {symbol:<15} -> NO FUTURE FOUND")
            
        time.sleep(0.1)

    if not futures_list:
        print("❌ No MCX futures found. Exiting.")
        return

    # ✅ Save MCX Futures mapping for BrokerClient to use
    # Structure: Token -> [Symbol, TradingSymbol, LotSize]
    nfo_map = {tok.split("|")[-1]: [sym, tsym, ls] for sym, tok, tsym, ls in futures_list}
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    map_path = os.path.join(base_dir, 'data', 'mcx_futures_map.json')
    import json
    with open(map_path, 'w') as f:
        json.dump(nfo_map, f, indent=4)
    print(f"💾 Saved MCX Futures mapping to {map_path}")

    # Update config/mcx/config.py
    config_path = os.path.join(base_dir, 'config', 'mcx', 'config.py')
    
    # Prepare the new list string
    new_config_lines = ["SYMBOLS_FUTURE_UNIVERSE = ["]
    for sym, tok, tsym, ls in futures_list:
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
