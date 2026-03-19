#!/usr/bin/env python3
"""
Test MCX LiveFeed via WebSocket
"""
import os
import sys
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir) 
from api_helper import ShoonyaApiPy
import datetime
import logging
import time
import yaml
import pyotp

logging.basicConfig(level=logging.INFO)

api = ShoonyaApiPy()

cred_path = os.path.join(base_dir, 'cred.yml')
with open(cred_path) as f:
    cred = yaml.load(f, Loader=yaml.FullLoader)

if cred.get('totp_key'):
    totp = pyotp.TOTP(cred['totp_key'].replace(" ", ""))
    factor2 = totp.now()
    print(f"🤖 Automated TOTP generated: {factor2}")
else:
    factor2 = cred.get('factor2', '')

ret = api.login(userid = cred['user'], password = cred['pwd'], twoFA=factor2, vendor_code=cred['vc'], api_secret=cred['apikey'], imei=cred['imei'])

if ret:
    print("Logged in successfully")
    
    # First, let's check what MCX tokens are available
    print("\n" + "="*60)
    print("Checking MCX tokens via subscribe (which uses scrip master):")
    print("="*60)
    
    # Try different token formats
    mcx_test_tokens = [
        ('GOLDTEN', 'Gold Feb'),
        ('GOLD', 'Gold'),
        ('SILVERMIC', 'Silver Mini'),
        ('CRUDEOIL', 'Crude Oil'),
        ('477176', 'Numeric token - Gold Feb'),  # We know this from earlier
    ]
    
    # Test with numeric tokens from instruments.json or known tokens
    # These are the numeric tokens for MCX futures
    numeric_tokens = [
        ('477176', 'GOLDTEN'),   # Gold Feb 2026
        ('477745', 'SILVERMIC'),  # Silver Mini Mar 2026
        ('477745', 'SILVERM'),    # Silver March 2026
        ('478745', 'CRUDEOIL'),   # Crude Oil
    ]
    
    SYMBOLDICT = {}
    quote_count = {'count': 0}
    
    def event_handler_quote_update(message):
        quote_count['count'] += 1
        print(f"\n[Quote #{quote_count['count']}] {message.get('tk')} | LTP: {message.get('lp')} | Volume: {message.get('v')}")
        
        key = message.get('e', '') + '|' + message.get('tk', '')
        SYMBOLDICT[key] = message
        
        # Stop after getting 5 quotes
        if quote_count['count'] >= 5:
            print("\n✅ Got 5 quotes, closing...")
            api.close_websocket()
    
    def open_callback():
        print("\n✅ WebSocket connected!")
        print("\nSubscribing to MCX symbols...")
        
        # Subscribe to MCX with numeric tokens
        for token, name in numeric_tokens:
            print(f"  Subscribing: MCX|{token} ({name})")
            api.subscribe(f'MCX|{token}', feed_type='d')
        
        # Also try with symbol names (just in case)
        for symbol, name in mcx_test_tokens:
            print(f"  Subscribing: MCX|{symbol} ({name}) [symbol name]")
            api.subscribe(f'MCX|{symbol}', feed_type='d')
    
    def event_handler_order_update(message):
        print(f"Order update: {message}")
    
    print("\nStarting WebSocket for MCX livefeed...")
    try:
        ret = api.start_websocket(
            order_update_callback=event_handler_order_update, 
            subscribe_callback=event_handler_quote_update, 
            socket_open_callback=open_callback
        )
        print(f"start_websocket returned: {ret}")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    
    if ret:
        print("WebSocket started, waiting for quotes...")
        # Wait up to 30 seconds for quotes
        for i in range(30):
            if quote_count['count'] >= 5:
                break
            time.sleep(1)
            print(f"Waiting... {i+1}s", end='\r')
        
        print("\n" + "="*60)
        print("RESULTS:")
        print("="*60)
        print(f"Total quotes received: {quote_count['count']}")
        print(f"Symbols in SYMBOLDICT: {list(SYMBOLDICT.keys())}")
        
        if SYMBOLDICT:
            print("\nSample quote data:")
            for k, v in SYMBOLDICT.items():
                print(f"  {k}: {v}")
        else:
            print("\n❌ NO QUOTES RECEIVED - LiveFeed not working for MCX!")
    else:
        print("❌ WebSocket failed to start!")
else:
    print("❌ Login failed!")
