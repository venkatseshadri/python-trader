import os
import re
import yaml
import json
from datetime import datetime
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orbiter.core.broker import BrokerClient

def audit_session(log_file):
    print(f"🕵️  Starting Margin Audit for: {os.path.basename(log_file)}")
    
    # 1. Setup Broker for Span Calculations
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cred_path = os.path.join(os.path.dirname(base_dir), 'ShoonyaApi-py', 'cred.yml')
    client = BrokerClient(cred_path, segment_name='nfo')
    client.login()
    
    # 2. Get Initial Limits
    limits = client.get_limits()
    if not limits:
        print("❌ Could not fetch broker limits. Using default ₹4.12L.")
        total_power = 412634.32
    else:
        total_power = limits['total_power']
    
    print(f"💰 Initial Buying Power: ₹{total_power:,.2f}")
    
    # 3. Process Log Events
    entry_re = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*sim_spread side=(\w+) atm=([\w\.]+) hedge=([\w\.]+) qty=(\d+)')
    pos_re = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*📈 POS (NFO\|\d+): PnL=₹(-?[\d\.]+)')
    
    events = [] # List of (timestamp, type, data)
    scans = {} # timestamp -> list of active tokens
    
    # Track the state of the session
    active_margins = {} # token -> margin_rs
    available_margin = total_power
    pnl_realized = 0.0
    
    with open(log_file, 'r') as f:
        for line in f:
            # Check for Entry
            m_entry = entry_re.search(line)
            if m_entry:
                ts, side, atm, hedge, qty = m_entry.groups()
                events.append((ts, 'ENTRY', {'atm': atm, 'hedge': hedge, 'qty': int(qty), 'side': side}))
            
            # Check for Scan (Active Positions)
            m_pos = pos_re.search(line)
            if m_pos:
                ts, token, pnl = m_pos.groups()
                if ts not in scans: scans[ts] = {}
                scans[ts][token] = float(pnl)

    # 4. Resolve Exits from Scan Deltas
    sorted_scans = sorted(scans.keys())
    for i in range(len(sorted_scans) - 1):
        current_ts = sorted_scans[i]
        next_ts = sorted_scans[i+1]
        
        current_tokens = set(scans[current_ts].keys())
        next_tokens = set(scans[next_ts].keys())
        
        exited = current_tokens - next_tokens
        for token in exited:
            last_pnl = scans[current_ts][token]
            events.append((next_ts, 'EXIT', {'token': token, 'pnl': last_pnl}))

    # 5. Chronological Audit
    events.sort(key=lambda x: x[0])
    peak_margin = 0.0
    
    print("\n📜 --- CHRONOLOGICAL MARGIN LOG ---")
    for ts, ev_type, data in events:
        if ev_type == 'ENTRY':
            spread = {
                'atm_symbol': data['atm'], 'hedge_symbol': data['hedge'], 
                'lot_size': data['qty'], 'side': data['side']
            }
            res = client.margin.calculate_span_for_spread(spread, client.api, client.conn.cred['user'])
            if res.get('ok'):
                m = res['total_margin']
                token = next((k for k, v in client.master.TOKEN_TO_SYMBOL.items() if v == data['atm']), data['atm'])
                full_token = f"NFO|{token}"
                active_margins[full_token] = m
                available_margin -= m
                peak_margin = max(peak_margin, total_power - available_margin)
                
                status = "✅ OK" if available_margin >= 0 else "🛑 OVER"
                print(f"[{ts}] {status} | ENTRY {data['atm']} | Margin: -₹{m:,.0f} | Available: ₹{available_margin:,.0f}")
        
        elif ev_type == 'EXIT':
            token = data['token']
            if token in active_margins:
                m = active_margins.pop(token)
                pnl = data['pnl']
                available_margin += m
                total_power += pnl
                pnl_realized += pnl
                print(f"[{ts}] 💸 EXIT  {token} | Margin: +₹{m:,.0f} | PnL: {pnl:+.2f} | Available: ₹{available_margin:,.0f}")

    print("\n🏁 --- FINAL AUDIT SUMMARY ---")
    print(f"🎯 Total Realized PnL: ₹{pnl_realized:,.2f}")
    print(f"⛰️  Peak Margin Used:  ₹{peak_margin:,.2f}")
    print(f"⚡ Capability Limit:   ₹{total_power - pnl_realized:,.2f}")
    
    if peak_margin > (total_power - pnl_realized):
        print("🚨 WARNING: At peak, your account was OVER-LEVERAGED in simulation.")
    else:
        print("💎 SUCCESS: Every trade in this session fit within your finance capability.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python audit.py <log_file>")
    else:
        audit_session(sys.argv[1])
