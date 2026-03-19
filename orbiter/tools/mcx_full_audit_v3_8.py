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

SYMBOLS = [
    'CRUDEOILM', 'NATGASMINI', 'SILVERMIC', 'SILVERM', 
    'GOLDM', 'GOLDTEN', 'GOLDGUINEA', 
    'ALUMINI', 'ZINCMINI', 'LEADMINI'
]

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
    print("🔐 Logging into Shoonya...")
    l_ret = api.login(userid=USER_ID, password=PASSWORD, twoFA=pyotp.TOTP(TOTP_KEY).now(), 
                      vendor_code=VC_CODE, api_secret=API_KEY, imei=IMEI)
    if not l_ret or l_ret.get('stat') != 'Ok': return print("❌ Login Failed.")

    print(f"✅ Audit Date: {datetime.date.today()} | Portfolio Size: {len(SYMBOLS)}\n")
    print(f"{'Symbol':<20} | {'Token':<8} | {'LTP':<10} | {'ADX':<6} | {'Status'}")
    print("-" * 70)

    trending, choppy = [], []
    for sym in SYMBOLS:
        token, tsym = get_futures_token(sym)
        if not token: continue

        q = api.get_quotes(exchange='MCX', token=token)
        now = int(time.time())
        h = api.get_time_price_series(exchange='MCX', token=token, starttime=now-(86400*5), endtime=now, interval=5)

        if q and q.get('stat') == 'Ok' and isinstance(h, list) and len(h) > 25:
            try:
                df = pd.DataFrame(h)
                hi, lo, cl = df['into'].astype(float).values, df['intl'].astype(float).values, df['intc'].astype(float).values
                adx = talib.ADX(hi, lo, cl, timeperiod=14)[-1]
                lp = float(q.get('lp', 0))
                
                status = "🔥" if adx > 25 else "💤"
                print(f"{tsym:<20} | {token:<8} | {lp:<10.2f} | {adx:<6.2f} | {status}")
                
                if adx > 25: trending.append((tsym, adx))
                else: choppy.append((tsym, adx))
            except: print(f"{tsym:<20} | Calc Error")
        time.sleep(0.1)

    print("\n" + "="*50)
    print("DIRECTOR'S MARKET SUMMARY")
    print("="*50)
    print(f"🔥 TRENDING: {', '.join([f'{s}({a:.1f})' for s, a in sorted(trending, key=lambda x: x[1], reverse=True)])}")
    print(f"💤 CHOPPY  : {', '.join([f'{s}({a:.1f})' for s, a in choppy])}")

if __name__ == "__main__":
    run_audit()
