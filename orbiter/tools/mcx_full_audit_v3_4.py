#!/usr/bin/env python3
import sys
import os
import time
import datetime
import pandas as pd
import numpy as np
import talib
import pyotp

script_dir = os.path.dirname(os.path.abspath(__file__))
shoonya_path = os.path.abspath(os.path.join(script_dir, '..', '..', 'ShoonyaApi-py'))
sys.path.insert(0, shoonya_path)

from api_helper import ShoonyaApiPy

TOTP_KEY = '74GC2ZH5Q54SY2RFF2GLLSKTFZ754Z6D'
USER_ID  = 'FA333160'
PASSWORD = 'Taknev80*'
API_KEY  = 'cb4299f4cd849a4983d5ad50322d8e2d'
VC_CODE  = 'FA333160_U'
IMEI     = 'C0FJFG7WW7'

SMALL_LOT_SYMBOLS = [
    'CRUDEOILM', 'NATGASMINI', 'SILVERMIC', 
    'SILVERM', 'GOLDPETAL', 'GOLDM', 
    'ALUMINI', 'ZINCMINI', 'LEADMINI'
]

api = ShoonyaApiPy()

def get_futures_token(symbol):
    search_queries = [symbol, f"{symbol}26", f"{symbol}MAR"]
    
    for query in search_queries:
        res = api.searchscrip(exchange='MCX', searchtext=query)
        if res and 'values' in res:
            valid = [i for i in res['values'] if 'exd' in i and i['exd']]
            for item in valid:
                tsym = item['tsym']
                if any(opt in tsym for opt in ['CE', 'PE', ' C', ' P']): continue
                if symbol == 'SILVERM' and 'MIC' in tsym: continue
                if tsym.startswith(symbol):
                    return item['token'], tsym
    return None, None

def run_audit():
    print("🔐 Connecting to Shoonya API...")
    otp = pyotp.TOTP(TOTP_KEY).now()
    l_ret = api.login(userid=USER_ID, password=PASSWORD, twoFA=otp, 
                      vendor_code=VC_CODE, api_secret=API_KEY, imei=IMEI)

    if not l_ret or l_ret.get('stat') != 'Ok':
        print("❌ Login Failed.")
        return

    print(f"✅ Logged in. Auditing Portfolio Trends...\n")
    print(f"{'Symbol':<20} | {'Token':<8} | {'LTP':<8} | {'ADX':<6} | {'Status'}")
    print("-" * 65)

    trending = []
    choppy = []

    for sym in SMALL_LOT_SYMBOLS:
        token, tsym = get_futures_token(sym)
        if not token:
            print(f"{sym:<20} | {'-':<8} | {'-':<8} | {'-':<6} | ⚪ NOT FOUND")
            continue

        quote = api.get_quotes(exchange='MCX', token=token)
        now = int(time.time())
        hist = api.get_time_price_series(exchange='MCX', token=token, 
                                        starttime=now-(86400*5), endtime=now, interval=5)

        if quote and quote.get('stat') == 'Ok' and isinstance(hist, list) and len(hist) > 20:
            try:
                lp = float(quote.get('lp', 0))
                df = pd.DataFrame(hist)
                h, l, c = df['into'].astype(float).values, df['intl'].astype(float).values, df['intc'].astype(float).values
                adx_val = talib.ADX(h, l, c, timeperiod=14)[-1]
                
                status = "🔥" if adx_val > 25 else "💤"
                print(f"{tsym:<20} | {token:<8} | {lp:<8.2f} | {adx_val:<6.2f} | {status}")
                
                if adx_val > 25: trending.append((tsym, adx_val))
                else: choppy.append((tsym, adx_val))
            except Exception as e:
                print(f"{tsym:<20} | ERROR: {str(e)[:15]}")
        else:
            print(f"{tsym:<20} | {'INACTIVE':<8} | {'-':<8} | {'-':<6} | ❌")
        
        time.sleep(0.1)

    print("\n" + "="*30)
    print(f"MARKET SUMMARY (Director's View)")
    print("="*30)
    print(f"TRENDING: {', '.join([f'{s}({a:.1f})' for s, a in trending])}")
    print(f"CHOPPY  : {', '.join([f'{s}({a:.1f})' for s, a in choppy])}")

if __name__ == "__main__":
    run_audit()
