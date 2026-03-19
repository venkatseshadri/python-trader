#!/usr/bin/env python3
"""
CRUDEOILM ADX Validation Script
Tests broker data to see why ADX calculation fails
"""
import sys
import os

# Add ShoonyaApi-py to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'ShoonyaApi-py'))

import pyotp
import pandas as pd
import talib
from api_helper import ShoonyaApiPy
import datetime

api = ShoonyaApiPy()

TOTP_KEY = '74GC2ZH5Q54SY2RFF2GLLSKTFZ754Z6D'
USER_ID = 'FA333160'
PASSWORD = 'Taknev80*'
API_KEY = 'cb4299f4cd849a4983d5ad50322d8e2d'
VC_CODE = 'FA333160_U'

TOKEN = '472790'
SYMBOL = 'CRUDEOILM'

def get_adx_value():
    # 1. Login
    otp = pyotp.TOTP(TOTP_KEY).now()
    ret = api.login(userid=USER_ID, password=PASSWORD, twoFA=otp, 
                    vendor_code=VC_CODE, api_secret=API_KEY, imei='C0FJFG7WW7')

    if not ret or ret.get('stat') != 'Ok':
        print("❌ Login Failed")
        return

    # 2. Fetch 1 day of data
    end_time = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(days=1)
    
    history = api.get_time_price_series(exchange='MCX', token=TOKEN, 
                                        starttime=str(start_time.timestamp()), 
                                        interval='1')

    if history and isinstance(history, list):
        df = pd.DataFrame(history)
        
        # Convert to numeric (Shoonya uses: into=open, inth=high, intl=low, intc=close)
        df['open'] = pd.to_numeric(df['into'])   # Open
        df['high'] = pd.to_numeric(df['inth'])   # High
        df['low'] = pd.to_numeric(df['intl'])    # Low
        df['close'] = pd.to_numeric(df['intc'])   # Close

        print(f"--- {SYMBOL} Analysis ---")
        print(f"Total candles: {len(df)}")
        print(f"Current Price: {df['close'].iloc[-1]}")
        
        # Count flat candles (high <= low)
        flat_count = (df['high'] <= df['low']).sum()
        print(f"Flat candles (high <= low): {flat_count}/{len(df)}")
        
        # Calculate ADX
        adx = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
        print(f"ADX array (first 20): {adx[:20]}")
        print(f"ADX array (last 5): {adx[-5:]}")
        
        latest_adx = adx.iloc[-1]
        print(f"Latest ADX: {latest_adx}")
        
        # Check for NaN
        import numpy as np
        nan_count = np.isnan(adx).sum()
        print(f"NaN in ADX array: {nan_count}/{len(adx)}")
        
        # Check DM values
        plus_dm = talib.PLUS_DM(df['high'], df['low'], timeperiod=14)
        minus_dm = talib.MINUS_DM(df['high'], df['low'], timeperiod=14)
        print(f"PLUS_DM last 5: {plus_dm.iloc[-5:].values}")
        print(f"MINUS_DM last 5: {minus_dm.iloc[-5:].values}")
        
        # Check ATR (should work)
        atr = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
        print(f"ATR last 5: {atr.iloc[-5:].values}")
        
        if latest_adx > 25:
            print("Status: Strong Trend")
        else:
            print("Status: Weak Trend/Sideways")

        print(f"--- {SYMBOL} Analysis ---")
        print(f"Total candles: {len(df)}")
        print(f"Current Price: {df['inc'].iloc[-1]}")
        
        # Count flat candles (high <= low)
        flat_count = (df['into'] <= df['inti']).sum()
        print(f"Flat candles (high <= low): {flat_count}/{len(df)}")
        
        # Calculate ADX
        adx = talib.ADX(df['into'], df['inti'], df['inc'], timeperiod=14)
        print(f"ADX array (first 20): {adx[:20]}")
        print(f"ADX array (last 5): {adx[-5:]}")
        
        latest_adx = adx[-1]
        print(f"Latest ADX: {latest_adx}")
        
        # Check for NaN
        import numpy as np
        nan_count = np.isnan(adx).sum()
        print(f"NaN in ADX array: {nan_count}/{len(adx)}")
        
        # Check DM values
        plus_dm = talib.PLUS_DM(df['into'], df['inti'], timeperiod=14)
        minus_dm = talib.MINUS_DM(df['into'], df['inti'], timeperiod=14)
        print(f"PLUS_DM last 5: {plus_dm[-5:]}")
        print(f"MINUS_DM last 5: {minus_dm[-5:]}")
        
        # Check ATR (should work)
        atr = talib.ATR(df['into'], df['inti'], df['inc'], timeperiod=14)
        print(f"ATR last 5: {atr[-5:]}")
        
        if latest_adx > 25:
            print("Status: Strong Trend")
        else:
            print("Status: Weak Trend/Sideways")
            
    else:
        print("❌ Could not fetch historical data")

if __name__ == "__main__":
    get_adx_value()
