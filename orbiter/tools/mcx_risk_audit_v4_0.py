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

CONFIG = {
    'CRUDEOILM':  {'lot': 10,  'margin_pct': 42.0},
    'NATGASMINI': {'lot': 250, 'margin_pct': 32.0},
    'SILVERMIC':  {'lot': 1,   'margin_pct': 12.0},
    'SILVERM':    {'lot': 5,   'margin_pct': 12.0},
    'GOLDM':      {'lot': 100, 'margin_pct': 14.0},
    'GOLDTEN':    {'lot': 10,  'margin_pct': 14.0},
    'GOLDGUINEA': {'lot': 8,   'margin_pct': 14.0},
    'ALUMINI':    {'lot': 1000,'margin_pct': 10.0},
    'ZINCMINI':   {'lot': 1000,'margin_pct': 12.0},
    'LEADMINI':   {'lot': 1000,'margin_pct': 10.0}
}

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

def get_my_balance():
    limits = api.get_limits()
    if limits and limits.get('stat') == 'Ok':
        return float(limits.get('cash', 0))
    return 0.0

def run_risk_audit():
    print(f"🔐 Initializing Risk Audit | {datetime.datetime.now().strftime('%H:%M:%S')}")
    l_ret = api.login(userid=USER_ID, password=PASSWORD, twoFA=pyotp.TOTP(TOTP_KEY).now(), 
                      vendor_code=VC_CODE, api_secret=API_KEY, imei=IMEI)
    if not l_ret or l_ret.get('stat') != 'Ok': return print("❌ Login Failed.")

    available_cash = get_my_balance()
    print(f"💰 Available Margin: ₹{available_cash:,.2f}")
    print(f"{'Symbol':<15} | {'LTP':<8} | {'Req. Margin':<12} | {'ADX':<6} | {'Tradable?'}")
    print("-" * 75)

    for sym, cfg in CONFIG.items():
        token, tsym = get_futures_token(sym)
        if not token: continue

        q = api.get_quotes(exchange='MCX', token=token)
        now = int(time.time())
        h = api.get_time_price_series(exchange='MCX', token=token, starttime=now-(86400*5), endtime=now, interval=5)

        if q and q.get('stat') == 'Ok' and isinstance(h, list) and len(h) > 25:
            try:
                lp = float(q['lp'])
                req_margin = (lp * cfg['lot'] * cfg['margin_pct']) / 100
                
                df = pd.DataFrame(h)
                hi, lo, cl = df['into'].astype(float).values, df['intl'].astype(float).values, df['intc'].astype(float).values
                adx = talib.ADX(hi, lo, cl, timeperiod=14)[-1]
                
                can_trade = "✅ YES" if available_cash >= req_margin else "❌ NO"
                trend_icon = "🔥" if adx > 25 else "💤"
                
                print(f"{sym:<15} | {lp:<8.1f} | ₹{req_margin:<10.0f} | {adx:<6.2f} | {can_trade} {trend_icon}")
            except: print(f"{sym:<15} | Calculation Error")
        time.sleep(0.1)

if __name__ == "__main__":
    run_risk_audit()
