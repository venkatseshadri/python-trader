#!/usr/bin/env python3
"""
🛠️ Utility: Update Futures Config
Scans NIFTY 50 stocks for current month Futures and updates config.py
Run this script to refresh SYMBOLS_FUTURE_UNIVERSE in config.py
"""
import sys
import os
import re
import time

# Ensure we can import from project root (orbiter/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.client import BrokerClient
import config.config as config
import logging

def main():
    print("🚀 Starting Futures Configuration Update...")
    
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.DEBUG)
    logging.getLogger("websocket").setLevel(logging.DEBUG)

    # Initialize BrokerClient
    # Path to cred.yml relative to orbiter root
    try:
        client = BrokerClient("../ShoonyaApi-py/cred.yml")
    except Exception:
        print("⚠️ Could not find cred.yml, trying default...")
        client = BrokerClient()
    
    if not client.login():
        print("❌ Login failed. Please check credentials/TOTP.")
        return

    # Use NFO specific config
    import config.nfo.config as nfo_config
    print(f"📊 Scanning {len(nfo_config.SYMBOLS_UNIVERSE)} symbols from SYMBOLS_UNIVERSE...")
    
    futures_list = []
    
    for token in nfo_config.SYMBOLS_UNIVERSE:
        # token format: 'NSE|2885'
        token_id = token.split("|")[-1]
        
        # Get symbol name (e.g., 'RELIANCE')
        symbol = client.get_symbol(token_id)
        
        # If symbol lookup failed (returns NSE|token), try to load mapping
        if "|" in symbol:
            if not client.TOKEN_TO_SYMBOL:
                client.load_symbol_mapping()
            symbol = client.TOKEN_TO_SYMBOL.get(token_id, symbol)
            
        if "|" in symbol:
            print(f"⚠️ Could not resolve symbol for {token}")
            continue
            
        # Find Future using searchscrip
        res = client.get_near_future(symbol, exchange='NFO')
        fut_token = res['token'] if res else None
        tsym = res['tsym'] if res else None
        
        if fut_token:
            print(f"✅ {symbol:<15} -> {fut_token} ({tsym})")
            futures_list.append((symbol, fut_token, tsym))
        else:
            print(f"❌ {symbol:<15} -> NO FUTURE FOUND")
            
        # Rate limit slightly
        time.sleep(0.1)

    if not futures_list:
        print("❌ No futures found. Exiting.")
        return

    # ✅ Save NFO Futures mapping for BrokerClient to use
    # Map token_id -> [symbol, tsym]
    nfo_map = {tok.split("|")[-1]: [sym, tsym] for sym, tok, tsym in futures_list}
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    map_path = os.path.join(base_dir, 'data', 'nfo_futures_map.json')
    import json
    with open(map_path, 'w') as f:
        json.dump(nfo_map, f, indent=4)
    print(f"💾 Saved NFO Futures mapping to {map_path}")

    # Prepare the new list string
    new_config_lines = ["SYMBOLS_FUTURE_UNIVERSE = ["]
    for sym, tok, tsym in futures_list:
        new_config_lines.append(f"    '{tok}',  # {sym}")
    new_config_lines.append("]")
    new_config_str = "\n".join(new_config_lines)

    # Update config/nfo/config.py
    config_path = os.path.join(base_dir, 'config', 'nfo', 'config.py')
    
    with open(config_path, 'r') as f:
        content = f.read()

    # Regex to replace existing SYMBOLS_FUTURE_UNIVERSE
    pattern = r"SYMBOLS_FUTURE_UNIVERSE\s*=\s*\[.*?\]"
    new_content = re.sub(pattern, new_config_str, content, flags=re.DOTALL)

    with open(config_path, 'w') as f:
        f.write(new_content)

    print(f"🎉 Config updated successfully: {config_path}")
    print(f"✅ Added {len(futures_list)} future tokens.")

if __name__ == "__main__":
    main()
