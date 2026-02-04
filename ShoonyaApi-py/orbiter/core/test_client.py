#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api_helper import ShoonyaApiPy
import yaml
import logging
import time

# Enable debug logging (REMOVE in production)
logging.basicConfig(level=logging.DEBUG)

print("🚀 ORBITER LIVE TRADING ENGINE")
print("=" * 50)

# Load YOUR credentials (ShoonyaApi-py/cred.yml)
with open('cred.yml') as f:
    cred = yaml.load(f, Loader=yaml.FullLoader)
    print(f"✅ Credentials loaded: {cred['user']}")

# Create API instance + LIVE data storage
api = ShoonyaApiPy()
SYMBOLDICT = {}

# 🔥 PRODUCTION QUOTE CALLBACK (with 'ts' safety fix)
def event_handler_quote_update(message):
    global SYMBOLDICT
    
    # SAFETY: Skip non-quote messages (fixes 'ts' ERROR)
    if 'ts' not in message or 'lp' not in message:
        return
        
    key = message['e'] + '|' + message['tk']
    SYMBOLDICT[key] = message
    
    # LIVE streaming (ALL symbols)
    tsym = message['ts']
    ltp = message['lp']
    volume = message.get('v', 'N/A')
    print(f"🔥 LIVE: {tsym} LTP: {ltp} | Vol: {volume}")

# 🚀 WEBSOCKET CONNECT CALLBACK
def open_callback():
    print("🚀 WEBSOCKET CONNECTED!")
    # YOUR TRADING SYMBOLS (from your watchlist)
    api.subscribe([
        'NSE|2885',    # RELIANCE-EQ  
        'NSE|11630',   # NTPC-EQ
        'NSE|3703',    # VIPIND-EQ
        'NSE|3045',    # SBIN-EQ
        'NSE|1333',    # HDFCBANK-EQ
    ], feed_type='d')
    print("✅ Subscribed: RELIANCE, NTPC, VIPIND, SBIN, HDFC")

# 📋 ORDER UPDATE CALLBACK (for live trading)
def event_handler_order_update(message):
    print(f"📋 ORDER: {message.get('status', 'N/A')} - {message.get('tsym', 'N/A')}")

# LOGIN (YOUR TOTP from Google Authenticator)
print("1️⃣ LOGGING IN...")
ret = api.login(
    userid=cred['user'],
    password=cred['pwd'], 
    twoFA=cred['factor2'],  # UPDATE every 30s: 050980 → 123456
    vendor_code=cred['vc'],
    api_secret=cred['apikey'],
    imei=cred['imei']
)

if ret:
    print("✅ LOGIN SUCCESS!")
    
    # START LIVE FEED
    print("2️⃣ STARTING LIVE FEED...")
    ret = api.start_websocket(
        order_update_callback=event_handler_order_update,  # LIVE orders
        subscribe_callback=event_handler_quote_update,     # LIVE quotes
        socket_open_callback=open_callback                 # Connection
    )
    
    print("\n🎯 ORBITER LIVE! Press Ctrl+C to stop")
    print("📊 Access: SYMBOLDICT['NSE|2885']['lp'] = RELIANCE LTP")
    
    try:
        while True:
            time.sleep(1)
            
            # SHOW ALL LIVE SYMBOLS (FIXED - not just RELIANCE)
            if SYMBOLDICT:
                print("\n📊 PORTFOLIO DASHBOARD:")
                for key in list(SYMBOLDICT.keys())[:5]:  # Top 5 symbols
                    symbol = SYMBOLDICT[key]
                    print(f"   {symbol['ts']:12s} ₹{symbol['lp']:8s} Vol:{symbol.get('v', 'N/A'):>10s}")
                
                # YOUR TRADING LOGIC READY
                reliance_ltp = SYMBOLDICT.get('NSE|2885', {}).get('lp', 0)
                if reliance_ltp and float(reliance_ltp) > 1450:
                    print("🟢 EMABULL BUY SIGNAL!")
                    # api.place_order(...)  # UNCOMMENT for LIVE TRADING
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        api.close_websocket()
        print("🎉 ORBITER SHUTDOWN COMPLETE!")
        
else:
    print("❌ LOGIN FAILED - Check TOTP in cred.yml")
    print("💡 Generate NEW TOTP: Google Authenticator → FA333160")
