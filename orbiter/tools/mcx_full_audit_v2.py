#!/usr/bin/env python3
import sys
import os
import time
import datetime
import pandas as pd
import numpy as np
import talib
import pyotp

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ShoonyaApi-py'))
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

def get_strict_token(search_term):
    res = api.searchscrip(exchange='MCX', searchtext=search_term)
    if res and 'values' in res:
        for item in res['values']:
            tsym = item['tsym']
            if search_term == 'SILVERM' and 'MIC' in tsym:
                continue
            if tsym.startswith(search_term):
                return item['token'], tsym
    return None, None

def run_audit():
    print("🔐 Connecting to Shoonya API...")
    try:
        otp = pyotp.TOTP(TOTP_KEY).now()
        l_ret = api.login(userid=USER_ID, password=PASSWORD, twoFA=otp, 
                          vendor_code=VC_CODE, api_secret=API_KEY, imei=IMEI)
    except Exception as e:
        print(f"❌ Connection Failed: {e}")
        return

    if not l_ret or l_ret.get('stat') != 'Ok':
        print(f"❌ Login Failed: {l_ret.get('emsg', 'Check Credentials/TOTP')}")
        return

    print(f"✅ Logged in. Analyzing {len(SMALL_LOT_SYMBOLS)} symbols...\n")
    print(f"{'Symbol':<15} | {'Token':<8} | {'LTP':<8} | {'Spread %':<8} | {'ADX':<6} | {'Status'}")
    print("-" * 85)

    for sym in SMALL_LOT_SYMBOLS:
        token, tsym = get_strict_token(sym)
        
        if not token:
            print(f"{sym:<15} | {'-':<8} | {'-':<8} | {'-':<8} | {'-':<6} | ⚪ NOT FOUND")
            continue

        quote = api.get_quotes(exchange='MCX', token=token)
        
        now = datetime.datetime.now()
        end_t = int(now.timestamp())
        start_t = int((now - datetime.timedelta(days=4)).timestamp())
        
        hist = api.get_time_price_series(exchange='MCX', token=token, 
                                        starttime=start_t, endtime=end_t, interval=5)

        if quote and quote.get('stat') == 'Ok' and isinstance(hist, list) and len(hist) > 20:
            try:
                lp = float(quote.get('lp', 0))
                bp = float(quote.get('bp1', 0))
                sp = float(quote.get('sp1', 0))
                spread = ((sp - bp) / lp * 100) if lp > 0 else 0
                
                df = pd.DataFrame(hist)
                h, l, c = df['into'].astype(float).values, df['intl'].astype(float).values, df['intc'].astype(float).values
                adx_val = talib.ADX(h, l, c, timeperiod=14)[-1]
                
                liq_icon = "🟢" if spread < 0.25 else "🔴"
                trend_icon = "🔥" if adx_val > 25 else "💤"
                
                print(f"{tsym:<15} | {token:<8} | {lp:<8.2f} | {spread:<8.3f}% | {adx_val:<6.2f} | {liq_icon} {trend_icon}")
            except Exception as e:
                print(f"{tsym:<15} | {token:<8} | ERROR: {str(e)[:20]}")
        else:
            print(f"{tsym:<15} | {token:<8} | {'INACTIVE':<8} | {'-':<8} | {'-':<6} | ❌ NO DATA")
        
        time.sleep(0.2)

if __name__ == "__main__":
    run_audit()
