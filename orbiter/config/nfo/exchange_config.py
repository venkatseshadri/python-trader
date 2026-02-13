import json
import os
from datetime import time as dt_time

# 🔥 NIFTY 50 F&O TOKENS
SYMBOLS_UNIVERSE = [
    'NSE|25', 'NSE|15083', 'NSE|157', 'NSE|236', 'NSE|5900', 'NSE|16669', 'NSE|317', 'NSE|16675', 
    'NSE|383', 'NSE|10604', 'NSE|694', 'NSE|20374', 'NSE|881', 'NSE|910', 'NSE|5097', 'NSE|1232', 
    'NSE|7229', 'NSE|1333', 'NSE|467', 'NSE|1363', 'NSE|1394', 'NSE|4963', 'NSE|1660', 'NSE|1594', 
    'NSE|11195', 'NSE|11723', 'NSE|18143', 'NSE|1922', 'NSE|11483', 'NSE|2031', 'NSE|10999', 'NSE|22377', 
    'NSE|11630', 'NSE|17963', 'NSE|2475', 'NSE|14977', 'NSE|2885', 'NSE|21808', 'NSE|4306', 'NSE|3045', 
    'NSE|3351', 'NSE|11536', 'NSE|3432', 'NSE|3456', 'NSE|3499', 'NSE|13538', 'NSE|3506', 'NSE|1964', 
    'NSE|11532', 'NSE|3787'
]

SYMBOLS_FUTURE_UNIVERSE = [
    'NFO|59194',  # ADANIENT
    'NFO|59202',  # ADANIPORTS
    'NFO|59208',  # APOLLOHOSP
    'NFO|59210',  # ASIANPAINT
    'NFO|59215',  # AXISBANK
    'NFO|59216',  # BAJAJ-AUTO
    'NFO|59255',  # BAJFINANCE
    'NFO|59254',  # BAJAJFINSV
    'NFO|59260',  # BEL
    'NFO|59264',  # BHARTIARTL
    'NFO|59289',  # CIPLA
    'NFO|59290',  # COALINDIA
    'NFO|59309',  # DRREDDY
    'NFO|59310',  # EICHERMOT
    'NFO|59311',  # ETERNAL
    'NFO|59340',  # GRASIM
    'NFO|59343',  # HCLTECH
    'NFO|59345',  # HDFCBANK
    'NFO|59346',  # HDFCLIFE
    'NFO|59348',  # HINDALCO
    'NFO|59350',  # HINDUNILVR
    'NFO|59353',  # ICICIBANK
    'NFO|59383',  # ITC
    'NFO|59375',  # INFY
    'NFO|59372',  # INDIGO
    'NFO|59391',  # JSWSTEEL
    'NFO|59389',  # JIOFIN
    'NFO|59397',  # KOTAKBANK
    'NFO|59403',  # LT
    'NFO|59415',  # M&M
    'NFO|59419',  # MARUTI
    'NFO|59420',  # MAXHEALTH
    'NFO|59433',  # NTPC
    'NFO|59430',  # NESTLEIND
    'NFO|59439',  # ONGC
    'NFO|59454',  # POWERGRID
    'NFO|59460',  # RELIANCE
    'NFO|59465',  # SBILIFE
    'NFO|59468',  # SHRIRAMFIN
    'NFO|59466',  # SBIN
    'NFO|59473',  # SUNPHARMA
    'NFO|59489',  # TCS
    'NFO|59481',  # TATACONSUM
    'NFO|59493',  # TMPV
    'NFO|59484',  # TATASTEEL
    'NFO|59490',  # TECHM
    'NFO|59492',  # TITAN
    'NFO|59496',  # TRENT
    'NFO|59498',  # ULTRACEMCO
    'NFO|59519',  # WIPRO
]

MARKET_OPEN = dt_time(9, 15)
MARKET_CLOSE = dt_time(15, 30)
OPTION_INSTRUMENT = 'OPTSTK'
EXECUTION_MODE = 'CREDIT_SPREAD'

# 🔥 ORB Window Parameters
ORB_START_TIME = dt_time(9, 15)
ORB_END_TIME = dt_time(9, 30)

# 🔥 Load NSE Holidays from data/nfo/holidays.json
_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_path = os.path.join(_base, 'data', 'nfo', 'holidays.json')
try:
    with open(_path) as f:
        _data = json.load(f)
        MARKET_HOLIDAYS = _data.get("2026", [])
except Exception:
    MARKET_HOLIDAYS = []
