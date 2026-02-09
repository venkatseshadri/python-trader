#!/usr/bin/env python3
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from client import BrokerClient  # ← YOUR WORKING IMPORT!

# Test the BrokerClient class
client = BrokerClient()
if client.login():
    client.start_live_feed(['NSE|2885', 'NSE|11630'])  # RELIANCE + NTPC
    
    try:
        while True:
            time.sleep(1)
            print(f"💰 RELIANCE: ₹{client.reliance_ltp:.2f}")
            print(f"⚡ NTPC: ₹{client.ntpc_ltp:.2f}")
            print("─" * 30)
    except KeyboardInterrupt:
        client.close()
        print("🎉 Shutdown complete!")
else:
    print("❌ Login failed - update TOTP in cred.yml")
