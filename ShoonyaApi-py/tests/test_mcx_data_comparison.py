#!/usr/bin/env python3
"""
Test MCX: Compare TPSeries (historical) vs LiveFeed (WebSocket)
Goal: See if either can provide data for EMA/SuperTrend calculation
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
import pytz

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
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(tz=ist)
    
    # Get today's trading hours
    lastBusDay = now_ist
    while lastBusDay.weekday() >= 5:
        lastBusDay = lastBusDay - datetime.timedelta(days=1)
    
    print(f"\n{'='*60}")
    print("TEST 1: TPSeries (Historical Data)")
    print(f"{'='*60}")
    
    # Test different time ranges
    test_configs = [
        # (start_offset_hours, end_offset_hours, description)
        (0, 2, "Last 2 hours"),
        (0, 5, "Last 5 hours"),  
        (-24, 0, "Last 24 hours"),
        (-48, 0, "Last 48 hours"),
    ]
    
    # Use numeric token for MCX Gold Feb 2026
    mcx_token = "477176"  # Gold Feb 2026
    mcx_exchange = "MCX"
    
    for start_offset, end_offset, desc in test_configs:
        start_dt = lastBusDay.replace(hour=9, minute=0, second=0, microsecond=0) + datetime.timedelta(hours=start_offset)
        end_dt = lastBusDay.replace(hour=9, minute=0, second=0, microsecond=0) + datetime.timedelta(hours=end_offset)
        
        print(f"\n--- {desc} ---")
        print(f"    Start: {start_dt} (ts: {start_dt.timestamp()})")
        print(f"    End:   {end_dt} (ts: {end_dt.timestamp()})")
        
        try:
            ret = api.get_time_price_series(
                exchange=mcx_exchange,
                token=mcx_token,
                starttime=start_dt.timestamp(),
                endtime=end_dt.timestamp(),
                interval=5  # 5 minute candles
            )
            if ret and len(ret) > 0:
                print(f"    ✅ SUCCESS! Got {len(ret)} candles")
                print(f"    First: {ret[0]}")
                print(f"    Last:  {ret[-1]}")
            else:
                print(f"    ❌ No data returned")
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    print(f"\n{'='*60}")
    print("TEST 2: LiveFeed (WebSocket) - Build Candles Over Time")
    print(f"{'='*60}")
    
    SYMBOLDICT = {}
    tick_count = {'total': 0}
    
    def event_handler_quote_update(message):
        tick_count['total'] += 1
        token = message.get('tk', '')
        exch = message.get('e', '')
        
        key = f"{exch}|{token}"
        SYMBOLDICT[key] = message
        
        if tick_count['total'] <= 5:
            print(f"\n[Tick #{tick_count['total']}] {key}")
            print(f"    LTP: {message.get('lp')}")
            print(f"    Open: {message.get('o')}, High: {message.get('h')}, Low: {message.get('l')}, Close: {message.get('c')}")
            print(f"    Volume: {message.get('v')}")
            print(f"    Time: {message.get('ltt')}")
    
    def open_callback():
        print("\n✅ WebSocket connected!")
        # Subscribe to MCX Gold
        print(f"    Subscribing to MCX|{mcx_token}...")
        api.subscribe(f'MCX|{mcx_token}', feed_type='d')
    
    def event_handler_order_update(message):
        pass
    
    print("\nStarting WebSocket...")
    ret = api.start_websocket(
        order_update_callback=event_handler_order_update, 
        subscribe_callback=event_handler_quote_update, 
        socket_open_callback=open_callback
    )
    
    if ret is not None:
        print("WebSocket started, collecting ticks for 20 seconds...")
        
        # Collect ticks for 20 seconds to build some candles
        for i in range(20):
            time.sleep(1)
            print(f"\rCollecting ticks... {i+1}/20 (total: {tick_count['total']})", end='')
        
        print(f"\n\n{'='*60}")
        print("TEST 3: TPSeries After LiveFeed Started")
        print(f"{'='*60}")
        
        # Try TPSeries again now that WebSocket is connected
        start_dt = lastBusDay.replace(hour=9, minute=0, second=0, microsecond=0)
        end_dt = now_ist
        
        print(f"\n--- After LiveFeed ---")
        print(f"    Start: {start_dt}")
        print(f"    End:   {end_dt}")
        
        try:
            ret = api.get_time_price_series(
                exchange=mcx_exchange,
                token=mcx_token,
                starttime=start_dt.timestamp(),
                endtime=end_dt.timestamp(),
                interval=5
            )
            if ret and len(ret) > 0:
                print(f"    ✅ SUCCESS! Got {len(ret)} candles")
                print(f"    First: {ret[0]}")
                print(f"    Last:  {ret[-1]}")
            else:
                print(f"    ❌ No data returned")
        except Exception as e:
            print(f"    ❌ Error: {e}")
        
        print(f"\n\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Total ticks received: {tick_count['total']}")
        print(f"Symbols with ticks: {list(SYMBOLDICT.keys())}")
        
        if tick_count['total'] > 0:
            sample = list(SYMBOLDICT.values())[0]
            print(f"\nSample tick data:")
            print(f"  Has 'o' (open):  {'o' in sample}")
            print(f"  Has 'h' (high):  {'h' in sample}")
            print(f"  Has 'l' (low):   {'l' in sample}")
            print(f"  Has 'c' (close): {'c' in sample}")
            print(f"  Has 'v' (volume):{'v' in sample}")
        
        print(f"\nConclusion:")
        print(f"  - TPSeries for MCX: {'WORKS' if ret and len(ret) > 0 else 'DOES NOT WORK (no historical data)'}")
        print(f"  - LiveFeed for MCX: {'WORKS' if tick_count['total'] > 0 else 'DOES NOT WORK'}")
        print(f"\nNote: LiveFeed provides single-tick data (current OHLC), not historical candles.")
        print(f"Need to either wait for candles to build OR find another data source.")
        
        api.close_websocket()
    else:
        print("❌ WebSocket failed to start!")

else:
    print("❌ Login failed!")
