import os
import sys
import yaml
import json
from datetime import date
from typing import Dict, Any, List

# Add project root to path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(base_dir))

from orbiter.core.broker import BrokerClient

def get_nifty_oi_analysis(client: BrokerClient):
    """
    📈 NIFTY Weekly OI Analyzer (v1.2) - Scrip Master Fallback
    """
    print("🔍 Fetching NIFTY Technicals...")
    
    nifty_fut = client.get_near_future('NIFTY', 'NFO')
    if not nifty_fut:
        print("❌ Could not resolve NIFTY future.")
        return
    
    quotes = client.api.get_quotes(exchange='NFO', token=nifty_fut['token'].split('|')[-1])
    if not quotes or 'lp' not in quotes:
        print("❌ API failed to return NIFTY LTP.")
        return
        
    ltp = float(quotes.get('lp', 0))
    print(f"🎯 NIFTY LTP: {ltp}")

    # 1. Get Today's Expiry Date
    today_str = date.today().isoformat()
    print(f"📅 Looking for Expiry: {today_str}")

    # 2. Filter Scrip Master for NIFTY Weekly Options
    print("📊 Searching Scrip Master for NIFTY weekly strikes...")
    weekly_options = [
        row for row in client.master.DERIVATIVE_OPTIONS
        if row.get('symbol') == 'NIFTY' and row.get('expiry') == today_str and row.get('instrument') == 'OPTIDX'
    ]

    if not weekly_options:
        print("⚠️  No weekly NIFTY options found for today in master.")
        # Try finding the VERY next expiry
        expiries = sorted({row['expiry'] for row in client.master.DERIVATIVE_OPTIONS if row.get('symbol') == 'NIFTY'})
        print(f"💡 Available NIFTY Expiries: {expiries[:3]}")
        return

    # 3. Analyze OI for strikes near ATM (+/- 500 points)
    atm_strike = round(ltp / 50) * 50
    target_options = [
        row for row in weekly_options 
        if abs(row['strike'] - atm_strike) <= 500
    ]

    print(f"📊 Fetching OI for {len(target_options)} strikes near {atm_strike}...")
    analysis = []
    for row in target_options:
        q = client.api.get_quotes(exchange='NFO', token=row['token'])
        if q and 'tsym' in q:
            analysis.append({
                'tsym': q['tsym'],
                'strike': float(row['strike']),
                'type': 'CALL' if q['tsym'].endswith('C') or 'CE' in q['tsym'] else 'PUT',
                'oi': int(q.get('oi', 0)),
                'lp': float(q.get('lp', 0))
            })

    # 4. Results
    calls = sorted([x for x in analysis if x['type'] == 'CALL'], key=lambda x: x['oi'], reverse=True)
    puts = sorted([x for x in analysis if x['type'] == 'PUT'], key=lambda x: x['oi'], reverse=True)

    print("\n🔥 --- NIFTY WEEKLY OI CLUSTERS (TODAY) ---")
    print("--- RESISTANCE (High Call OI) ---")
    for c in calls[:3]:
        print(f"  • {c['strike']}: OI {c['oi']:,} | LTP ₹{c['lp']:.2f}")
    
    print("\n--- SUPPORT (High Put OI) ---")
    for p in puts[:3]:
        print(f"  • {p['strike']}: OI {p['oi']:,} | LTP ₹{p['lp']:.2f}")
    print("-" * 40)

if __name__ == "__main__":
    cred_path = os.path.join(os.path.dirname(base_dir), 'ShoonyaApi-py/cred.yml')
    client = BrokerClient(cred_path, segment_name='nfo')
    if client.login():
        get_nifty_oi_analysis(client)
