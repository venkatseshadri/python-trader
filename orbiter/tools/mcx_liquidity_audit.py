#!/usr/bin/env python3
"""
MCX Liquidity Audit Script
Checks which MCX tokens have sufficient historical data from broker API
"""
import sys
import os

# Add ShoonyaApi-py to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ShoonyaApi-py'))

import pyotp
from api_helper import ShoonyaApiPy
import time

api = ShoonyaApiPy()

TOTP_KEY = '74GC2ZH5Q54SY2RFF2GLLSKTFZ754Z6D'

MCX_TOKENS = {
    '487655': 'ALUMINI',
    '472790': 'CRUDEOILM',
    '487659': 'LEADMINI',
    '475112': 'NATGASMINI',
    '466029': 'SILVERMIC',
    '457533': 'SILVERM',
    '477904': 'GOLDM',
    '477176': 'GOLDTEN',
    '477174': 'GOLDGUINEA',
    '487663': 'ZINCMINI'
}

USER_ID = 'FA333160'
PASSWORD = 'Taknev80*'
API_KEY = 'cb4299f4cd849a4983d5ad50322d8e2d'
VC_CODE = 'FA333160_U'
IMEI = 'C0FJFG7WW7'

def audit_mcx_data():
    token_2fa = pyotp.TOTP(TOTP_KEY).now()
    login_ret = api.login(userid=USER_ID, password=PASSWORD, twoFA=token_2fa, 
                          vendor_code=VC_CODE, api_secret=API_KEY, imei=IMEI)

    if not login_ret or login_ret.get('stat') != 'Ok':
        print("❌ Login Failed.")
        return

    print(f"✅ Logged in. Auditing {len(MCX_TOKENS)} tokens...\n")
    print(f"{'Symbol':<12} | {'Token':<8} | {'LTP':<10} | {'Bid':<10} | {'Ask':<10} | {'Spread %':<10} | {'Status'}")
    print("-" * 90)

    results = []
    for token, symbol in MCX_TOKENS.items():
        quote = api.get_quotes(exchange='MCX', token=token)
        
        if quote and quote.get('stat') == 'Ok':
            lp = float(quote.get('lp', 0))
            bp1 = float(quote.get('bp1', 0))
            sp1 = float(quote.get('sp1', 0))
            
            if lp > 0 and bp1 > 0:
                spread_pct = ((sp1 - bp1) / lp) * 100
                status = "🟢 LIQUID" if spread_pct < 0.15 else "🔴 ILLIQUID"
                print(f"{symbol:<12} | {token:<8} | {lp:<10} | {bp1:<10} | {sp1:<10} | {spread_pct:.4f}%    | {status}")
                results.append({'symbol': symbol, 'token': token, 'lp': lp, 'spread': spread_pct, 'status': status})
            else:
                print(f"{symbol:<12} | {token:<8} | {'NO DATA':<10} | {'-':<10} | {'-':<10} | {'-':<10}    | ⚪ INACTIVE")
                results.append({'symbol': symbol, 'token': token, 'status': 'INACTIVE'})
        else:
            print(f"{symbol:<12} | {token:<8} | {'ERROR':<10} | {'-':<10} | {'-':<10} | {'-':<10}    | ❌ ERROR")
            results.append({'symbol': symbol, 'token': token, 'status': 'ERROR'})
        
        time.sleep(0.15)

    # Now test historical data
    print("\n\n=== HISTORICAL DATA TEST ===")
    print(f"{'Symbol':<12} | {'Token':<8} | {'Candles':<8} | {'Status'}")
    print("-" * 45)
    
    import datetime
    end_time = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(minutes=120)
    
    for token, symbol in MCX_TOKENS.items():
        hist = api.get_time_price_series(
            exchange='MCX',
            token=token,
            starttime=start_time.timestamp(),
            endtime=end_time.timestamp(),
            interval=5
        )
        
        if hist and isinstance(hist, list) and len(hist) > 10:
            print(f"{symbol:<12} | {token:<8} | {len(hist):<8} | ✅ OK")
        else:
            count = len(hist) if hist and isinstance(hist, list) else 0
            print(f"{symbol:<12} | {token:<8} | {count:<8} | ❌ INSUFFICIENT")
        
        time.sleep(0.15)

if __name__ == "__main__":
    audit_mcx_data()
