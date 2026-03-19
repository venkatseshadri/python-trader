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

api = ShoonyaApiPy()

def explore_gold_tokens():
    print("🔍 Searching for ALL Gold-related contracts...")
    search_terms = ['GOLD', 'PETAL', 'GUINEA']
    found_tokens = []

    for term in search_terms:
        res = api.searchscrip(exchange='MCX', searchtext=term)
        if res and 'values' in res:
            for item in res['values']:
                tsym = item['tsym']
                if any(x in tsym for x in ['CE', 'PE', ' C ', ' P ']): continue
                if 'exd' in item:
                    found_tokens.append({'tsym': tsym, 'token': item['token'], 'expiry': item['exd']})

    found_tokens.sort(key=lambda x: x['tsym'])
    
    print(f"{'Trading Symbol':<20} | {'Token ID':<10} | {'Expiry'}")
    print("-" * 50)
    for t in found_tokens:
        print(f"{t['tsym']:<20} | {t['token']:<10} | {t['expiry']}")
    return found_tokens

def run_gold_audit(gold_list):
    print("\n📈 Running ADX Audit on Gold Portfolio...")
    print(f"{'Symbol':<20} | {'LTP':<10} | {'ADX':<6} | {'Status'}")
    print("-" * 50)

    for item in gold_list:
        token = item['token']
        tsym = item['tsym']
        
        if not any(match in tsym for match in ['GOLDPETAL', 'GOLDM', 'GOLDGUINEA']):
            continue

        q = api.get_quotes(exchange='MCX', token=token)
        now = int(time.time())
        h = api.get_time_price_series(exchange='MCX', token=token, starttime=now-(86400*5), endtime=now, interval=5)

        if q and q.get('stat') == 'Ok' and isinstance(h, list) and len(h) > 25:
            try:
                df = pd.DataFrame(h)
                high, low, close = df['into'].astype(float).values, df['intl'].astype(float).values, df['intc'].astype(float).values
                adx_val = talib.ADX(high, low, close, timeperiod=14)[-1]
                
                status = "🔥" if adx_val > 25 else "💤"
                print(f"{tsym:<20} | {float(q['lp']):<10.2f} | {adx_val:<6.2f} | {status}")
            except:
                print(f"{tsym:<20} | Error calculating ADX")
        time.sleep(0.1)

if __name__ == "__main__":
    print("🔐 Logging into Shoonya...")
    l_ret = api.login(userid=USER_ID, password=PASSWORD, twoFA=pyotp.TOTP(TOTP_KEY).now(), 
                      vendor_code=VC_CODE, api_secret=API_KEY, imei=IMEI)
    
    if l_ret and l_ret.get('stat') == 'Ok':
        all_gold = explore_gold_tokens()
        run_gold_audit(all_gold)
    else:
        print("❌ Login Failed.")
