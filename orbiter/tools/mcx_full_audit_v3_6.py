#!/usr/bin/env python3
import sys, os, time, datetime
import pandas as pd
import numpy as np
import talib
import pyotp

script_dir = os.path.dirname(os.path.abspath(__file__))
shoonya_path = os.path.abspath(os.path.join(script_dir, '..', '..', 'ShoonyaApi-py'))
sys.path.insert(0, shoonya_path)

from api_helper import ShoonyaApiPy

TOTP_KEY = '74GC2ZH5Q54SY2RFF2GLLSKTFZ754Z6D'
USER_ID, PASSWORD = 'FA333160', 'Taknev80*'
API_KEY, VC_CODE, IMEI = 'cb4299f4cd849a4983d5ad50322d8e2d', 'FA333160_U', 'C0FJFG7WW7'

SYMBOLS = ['CRUDEOILM', 'NATGASMINI', 'SILVERMIC', 'SILVERM', 'GOLDPETAL', 'GOLDM', 'ALUMINI', 'ZINCMINI', 'LEADMINI']

api = ShoonyaApiPy()

def get_futures_token(symbol):
    res = api.searchscrip(exchange='MCX', searchtext=symbol)
    
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
    try:
        otp = pyotp.TOTP(TOTP_KEY).now()
        l_ret = api.login(userid=USER_ID, password=PASSWORD, twoFA=otp, 
                          vendor_code=VC_CODE, api_secret=API_KEY, imei=IMEI)
    except Exception as e:
        return print(f"❌ Connection Failed: {e}")

    if not l_ret or l_ret.get('stat') != 'Ok':
        return print(f"❌ Login Failed: {l_ret.get('emsg', 'Check Credentials')}")

    print(f"✅ Logged in. Analyzing Portfolio (Date: {datetime.date.today()})\n")
    print(f"{'Symbol':<20} | {'Token':<8} | {'LTP':<10} | {'ADX':<6} | {'Status'}")
    print("-" * 70)

    trending, choppy = [], []
    
    for sym in SYMBOLS:
        token, tsym = get_futures_token(sym)
        if not token:
            print(f"{sym:<20} | {'-':<8} | {'-':<10} | {'-':<6} | ⚪ NOT FOUND")
            continue

        q = api.get_quotes(exchange='MCX', token=token)
        now = int(time.time())
        h = api.get_time_price_series(exchange='MCX', token=token, starttime=now-(86400*5), endtime=now, interval=5)

        if q and q.get('stat') == 'Ok' and isinstance(h, list) and len(h) > 25:
            try:
                df = pd.DataFrame(h)
                high = df['into'].astype(float).values
                low = df['intl'].astype(float).values
                close = df['intc'].astype(float).values
                
                adx_val = talib.ADX(high, low, close, timeperiod=14)[-1]
                lp = float(q.get('lp', 0))
                
                status = "🔥" if adx_val > 25 else "💤"
                print(f"{tsym:<20} | {token:<8} | {lp:<10.2f} | {adx_val:<6.2f} | {status}")
                
                if adx_val > 25: trending.append((tsym, adx_val))
                else: choppy.append((tsym, adx_val))
            except Exception as e:
                print(f"{tsym:<20} | ERROR in Calculation: {str(e)[:15]}")
        else:
            print(f"{tsym:<20} | {'NO DATA':<8} | {'-':<10} | {'-':<6} | ❌ INACTIVE")
        
        time.sleep(0.15)

    print("\n" + "="*50)
    print(f"MARKET SUMMARY (Director's Portfolio)")
    print("="*50)
    if trending:
        print(f"🔥 TRENDING: {', '.join([f'{s}({a:.1f})' for s, a in sorted(trending, key=lambda x: x[1], reverse=True)])}")
    if choppy:
        print(f"💤 CHOPPY  : {', '.join([f'{s}({a:.1f})' for s, a in choppy])}")
    print("="*50)

if __name__ == "__main__":
    run_audit()
