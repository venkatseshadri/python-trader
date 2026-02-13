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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

    print(f"📊 Scanning {len(config.SYMBOLS_UNIVERSE)} symbols from SYMBOLS_UNIVERSE...")
    
    futures_list = []
    
    for token in config.SYMBOLS_UNIVERSE:
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
        ret = client.api.searchscrip(exchange='NFO', searchtext=symbol)
        fut_token = None
        tsym = None
        if ret and ret.get('stat') == 'Ok' and 'values' in ret:
            candidates = []
            import datetime
            today = datetime.date.today()
            for scrip in ret['values']:
                if scrip.get('instname') in ('FUTSTK', 'FUTIDX') and scrip.get('symname') == symbol:
                    exp_str = scrip.get('exp') or scrip.get('exd')
                    exp = client._parse_expiry_date(exp_str)
                    if exp and exp >= today:
                        candidates.append((exp, scrip['token'], scrip.get('tsym')))
            
            if candidates:
                candidates.sort(key=lambda x: x[0])
                fut_token = f"NFO|{candidates[0][1]}"
                tsym = candidates[0][2]
        
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
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

    # Update config.py
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.py')
    
    with open(config_path, 'r') as f:
        content = f.read()

    # Regex to replace existing SYMBOLS_FUTURE_UNIVERSE or append
    pattern = r"SYMBOLS_FUTURE_UNIVERSE\s*=\s*\[.*?\]"
    
    if re.search(pattern, content, re.DOTALL):
        print("\n🔄 Updating existing SYMBOLS_FUTURE_UNIVERSE in config.py...")
        new_content = re.sub(pattern, new_config_str, content, flags=re.DOTALL)
    else:
        print("\n➕ Appending SYMBOLS_FUTURE_UNIVERSE to config.py...")
        new_content = content + "\n\n" + new_config_str + "\n"

    with open(config_path, 'w') as f:
        f.write(new_content)

    print(f"🎉 Config updated successfully: {config_path}")
    print(f"✅ Added {len(futures_list)} future tokens.")

if __name__ == "__main__":
    main()
