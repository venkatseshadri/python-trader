#!/usr/bin/env python3
"""
Test MCX historical data retrieval from Shoonya API
"""
import os
import sys
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir) 
from api_helper import ShoonyaApiPy
import logging
import yaml
import datetime
import timeit
import pytz
import pyotp

logging.basicConfig(level=logging.DEBUG)

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
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(tz=ist)
    
    # Get today's date or yesterday if weekend
    lastBusDay = now_ist
    while lastBusDay.weekday() >= 5:
        lastBusDay = lastBusDay - datetime.timedelta(days=1)
    
    print(f"Testing with date: {lastBusDay.date()}")
    
    # MCX trading hours: 9 AM to 11:55 PM IST
    start_dt = lastBusDay.replace(hour=9, minute=0, second=0, microsecond=0)
    end_dt = lastBusDay.replace(hour=23, minute=55, second=0, microsecond=0)
    
    print(f"Start: {start_dt}")
    print(f"End: {end_dt}")
    print(f"Start timestamp: {start_dt.timestamp()}")
    print(f"End timestamp: {end_dt.timestamp()}")
    
    # Test MCX symbols - using symbol names (not numeric tokens)
    mcx_symbols = [
        ('GOLDTEN', 'Gold February'),
        ('SILVERM', 'Silver March'),
        ('CRUDEOIL', 'Crude Oil'),
        ('NATURALGAS', 'Natural Gas'),
        ('COPPER', 'Copper'),
        ('ZINC', 'Zinc'),
        ('NICKEL', 'Nickel'),
        ('LEAD', 'Lead'),
        ('ALUMINIUM', 'Aluminium'),
    ]
    
    # First, let's see what tokens are available
    print("\n" + "="*60)
    print("Testing get_security_info for MCX symbols:")
    print("="*60)
    
    for symbol, name in mcx_symbols[:3]:  # Test first 3
        print(f"\n--- {symbol} ({name}) ---")
        try:
            info = api.get_security_info(exchange='MCX', token=symbol)
            print(f"Security info: {info}")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n" + "="*60)
    print("Testing get_time_price_series:")
    print("="*60)
    
    # Try with symbol name
    for symbol, name in mcx_symbols[:3]:
        print(f"\n--- {symbol} ({name}) ---")
        try:
            # Try with 5 minute interval
            ret = api.get_time_price_series(
                exchange='MCX',
                token=symbol,
                starttime=start_dt.timestamp(),
                endtime=end_dt.timestamp(),
                interval=5  # 5 minutes
            )
            if ret:
                print(f"✅ Got {len(ret)} candles with symbol name!")
                print(f"First candle: {ret[0] if ret else 'None'}")
            else:
                print("❌ No data returned with symbol name")
        except Exception as e:
            print(f"❌ Error with symbol name: {e}")
        
        # Try with numeric token
        try:
            # Get the token first
            info = api.get_security_info(exchange='MCX', token=symbol)
            if info and 'token' in info:
                num_token = info['token']
                print(f"  Numeric token: {num_token}")
                
                ret = api.get_time_price_series(
                    exchange='MCX',
                    token=num_token,
                    starttime=start_dt.timestamp(),
                    endtime=end_dt.timestamp(),
                    interval=5
                )
                if ret:
                    print(f"✅ Got {len(ret)} candles with numeric token!")
                    print(f"First candle: {ret[0] if ret else 'None'}")
                else:
                    print("❌ No data returned with numeric token")
        except Exception as e:
            print(f"❌ Error with numeric token: {e}")
    
    # Also test NSE for comparison
    print("\n" + "="*60)
    print("Testing NSE for comparison (should work):")
    print("="*60)
    try:
        nse_start = lastBusDay.replace(hour=9, minute=15, second=0, microsecond=0)
        nse_end = lastBusDay.replace(hour=15, minute=30, second=0, microsecond=0)
        
        ret = api.get_time_price_series(
            exchange='NSE',
            token='26000',  # NIFTY 50
            starttime=nse_start.timestamp(),
            endtime=nse_end.timestamp(),
            interval=5
        )
        if ret:
            print(f"✅ NSE: Got {len(ret)} candles")
            print(f"First candle: {ret[0] if ret else 'None'}")
        else:
            print("❌ NSE: No data")
    except Exception as e:
        print(f"❌ NSE Error: {e}")

else:
    print("Login failed!")
