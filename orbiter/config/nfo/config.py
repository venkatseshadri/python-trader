import json
import os
from datetime import time as dt_time

# 🔥 NIFTY 50 F&O TOKENS
SYMBOLS_UNIVERSE = [
    'NSE|26000', # NIFTY Index
    'NSE|25', 'NSE|15083', 'NSE|157', 'NSE|236', 'NSE|5900', 'NSE|16669', 'NSE|317', 'NSE|16675', 

    'NSE|383', 'NSE|10604', 'NSE|694', 'NSE|20374', 'NSE|881', 'NSE|910', 'NSE|5097', 'NSE|1232', 
    'NSE|7229', 'NSE|1333', 'NSE|467', 'NSE|1363', 'NSE|1394', 'NSE|4963', 'NSE|1660', 'NSE|1594', 
    'NSE|11195', 'NSE|11723', 'NSE|18143', 'NSE|1922', 'NSE|11483', 'NSE|2031', 'NSE|10999', 'NSE|22377', 
    'NSE|11630', 'NSE|17963', 'NSE|2475', 'NSE|14977', 'NSE|2885', 'NSE|21808', 'NSE|4306', 'NSE|3045', 
    'NSE|3351', 'NSE|11536', 'NSE|3432', 'NSE|3456', 'NSE|3499', 'NSE|13538', 'NSE|3506', 'NSE|1964', 
    'NSE|11532', 'NSE|3787'
]

SYMBOLS_FUTURE_UNIVERSE = [
    'NFO|51714', # NIFTY Monthly Future
    'NFO|59194', 'NFO|59202', 'NFO|59208', 'NFO|59210', 'NFO|59215', 'NFO|59216', 'NFO|59255', 


    'NFO|59254', 'NFO|59260', 'NFO|59264', 'NFO|59289', 'NFO|59290', 'NFO|59309', 'NFO|59310', 
    'NFO|59311', 'NFO|59340', 'NFO|59343', 'NFO|59345', 'NFO|59346', 'NFO|59348', 'NFO|59350', 
    'NFO|59353', 'NFO|59383', 'NFO|59375', 'NFO|59372', 'NFO|59391', 'NFO|59389', 'NFO|59397', 
    'NFO|59403', 'NFO|59415', 'NFO|59419', 'NFO|59420', 'NFO|59433', 'NFO|59430', 'NFO|59439', 
    'NFO|59454', 'NFO|59460', 'NFO|59465', 'NFO|59468', 'NFO|59466', 'NFO|59473', 'NFO|59489', 
    'NFO|59481', 'NFO|59493', 'NFO|59484', 'NFO|59490', 'NFO|59492', 'NFO|59496', 'NFO|59498', 'NFO|59519'
]

MARKET_OPEN = dt_time(9, 15)
MARKET_CLOSE = dt_time(15, 30)
OPTION_INSTRUMENT = 'OPTSTK'

# 🔥 Load NSE Holidays from data/nfo/holidays.json
_base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_path = os.path.join(_base, 'data', 'nfo', 'holidays.json')
try:
    with open(_path) as f:
        _data = json.load(f)
        MARKET_HOLIDAYS = _data.get("2026", [])
except Exception:
    MARKET_HOLIDAYS = []
