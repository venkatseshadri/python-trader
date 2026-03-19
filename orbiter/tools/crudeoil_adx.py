#!/usr/bin/env python3
import sys
import os
import datetime
import time
import pandas as pd
import numpy as np
import talib
import pyotp

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ShoonyaApi-py'))
from api_helper import ShoonyaApiPy

api = ShoonyaApiPy()

TOTP_KEY = '74GC2ZH5Q54SY2RFF2GLLSKTFZ754Z6D'
USER_ID = 'FA333160'
PASSWORD = 'Taknev80*'
API_KEY = 'cb4299f4cd849a4983d5ad50322d8e2d'
VC_CODE = 'FA333160_U'
IMEI = 'C0FJFG7WW7'

TOKEN = '472790'

def get_trend_analysis():
    token_2fa = pyotp.TOTP(TOTP_KEY).now()
    ret = api.login(userid=USER_ID, password=PASSWORD, twoFA=token_2fa, 
                    vendor_code=VC_CODE, api_secret=API_KEY, imei=IMEI)

    if not ret or ret.get('stat') != 'Ok':
        print("❌ Login Failed.")
        return

    end_time = int(datetime.datetime.now().timestamp())
    start_time = int((datetime.datetime.now() - datetime.timedelta(days=3)).timestamp())

    print(f"📡 Fetching data for Token {TOKEN}...")
    
    hist = api.get_time_price_series(exchange='MCX', token=TOKEN, 
                                     starttime=start_time, endtime=end_time, interval=5)

    if not hist or not isinstance(hist, list):
        print("❌ Error: No historical data returned. (Market might be closed or API down)")
        return

    if len(hist) < 30:
        print(f"⚠️ Warning: Only {len(hist)} candles found. ADX needs at least 30 to be accurate.")
        return

    df = pd.DataFrame(hist)
    df['h'] = df['into'].astype(float)
    df['l'] = df['intl'].astype(float)
    df['c'] = df['intc'].astype(float)

    df['adx'] = talib.ADX(df['h'].values, df['l'].values, df['c'].values, timeperiod=14)

    latest_adx = df['adx'].iloc[-1]
    
    if np.isnan(latest_adx):
        print("⚠️ ADX is still NaN. Fetch a longer time range.")
    else:
        print(f"✅ Analysis Complete: CRUDEOILM ADX is {latest_adx:.2f}")
        if latest_adx > 25:
            print("🔥 Trending Market Detected.")
        else:
            print("💤 Choppy/Sideways Market.")

if __name__ == "__main__":
    get_trend_analysis()
