#!/usr/bin/env python3
import sys
import os
import time
import datetime
import pandas as pd
import talib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ShoonyaApi-py'))

from api_helper import ShoonyaApiPy
import pyotp

api = ShoonyaApiPy()

TOTP_KEY = '74GC2ZH5Q54SY2RFF2GLLSKTFZ754Z6D'
USER_ID = 'FA333160'
PASSWORD = 'Taknev80*'
API_KEY = 'cb4299f4cd849a4983d5ad50322d8e2d'
VC_CODE = 'FA333160_U'
IMEI = 'C0FJFG7WW7'

MCX_TOKENS = {
    '474790': 'CRUDEOILM',
    '475112': 'NATGASMINI',
    '466029': 'SILVERMIC',
    '477175': 'GOLDPETAL',
    '487000': 'GOLDM',
    '487655': 'ALUMINI',
    '487663': 'ZINCMINI',
    '487659': 'LEADMINI',
    '487657': 'SILVERM'
}

def audit_and_trend():
    token_2fa = pyotp.TOTP(TOTP_KEY).now()
    login_ret = api.login(userid=USER_ID, password=PASSWORD, twoFA=token_2fa, 
                          vendor_code=VC_CODE, api_secret=API_KEY, imei=IMEI)

    if not login_ret or login_ret.get('stat') != 'Ok':
        print("❌ Login Failed.")
        return

    print(f"✅ Logged in. Auditing Small Lot Portfolio...\n")
    print(f"{'Symbol':<12} | {'LTP':<8} | {'Spread %':<8} | {'ADX(14)':<7} | {'Status'}")
    print("-" * 65)

    for token, symbol in MCX_TOKENS.items():
        quote = api.get_quotes(exchange='MCX', token=token)
        
        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(days=2)
        hist = api.get_time_price_series(exchange='MCX', token=token, 
                                        starttime=start_time.timestamp(), interval=5)

        if quote and quote.get('stat') == 'Ok' and hist and isinstance(hist, list) and len(hist) > 20:
            lp = float(quote.get('lp', 0))
            bp = float(quote.get('bp1', 0))
            sp = float(quote.get('sp1', 0))
            spread_pct = ((sp - bp) / lp * 100) if lp > 0 else 0
            
            df = pd.DataFrame(hist)
            df['h'], df['l'], df['c'] = pd.to_numeric(df['inth']), pd.to_numeric(df['intl']), pd.to_numeric(df['intc'])
            adx_arr = talib.ADX(df['h'], df['l'], df['c'], timeperiod=14)
            latest_adx = adx_arr[-1] if not pd.isna(adx_arr[-1]) else 0
            
            liq_status = "🟢" if spread_pct < 0.2 else "🔴"
            trend_status = "🔥" if latest_adx > 25 else "💤"
            
            print(f"{symbol:<12} | {lp:<8} | {spread_pct:.3f}% | {latest_adx:.2f}  | {liq_status} {trend_status}")
        else:
            print(f"{symbol:<12} | {'ERROR':<8} | {'-':<8} | {'-':<7} | ❌ DATA MISSING")
        
        time.sleep(0.2)

if __name__ == "__main__":
    audit_and_trend()
