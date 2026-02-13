"""
ORBITER CONFIG: NIFTY 50 F&O STOCKS ONLY (All have active F&O contracts)
"""

from datetime import time as dt_time

# 🔥 NIFTY 50 F&O TOKENS (from ind_nifty50list.csv + nse_token_map.json)
SYMBOLS_UNIVERSE = [
    'NSE|25',  # ADANIENT
    'NSE|15083',  # ADANIPORTS
    'NSE|157',  # APOLLOHOSP
    'NSE|236',  # ASIANPAINT
    'NSE|5900',  # AXISBANK
    'NSE|16669',  # BAJAJ-AUTO
    'NSE|317',  # BAJFINANCE
    'NSE|16675',  # BAJAJFINSV
    'NSE|383',  # BEL
    'NSE|10604',  # BHARTIARTL
    'NSE|694',  # CIPLA
    'NSE|20374',  # COALINDIA
    'NSE|881',  # DRREDDY
    'NSE|910',  # EICHERMOT
    'NSE|5097',  # ETERNAL
    'NSE|1232',  # GRASIM
    'NSE|7229',  # HCLTECH
    'NSE|1333',  # HDFCBANK
    'NSE|467',  # HDFCLIFE
    'NSE|1363',  # HINDALCO
    'NSE|1394',  # HINDUNILVR
    'NSE|4963',  # ICICIBANK
    'NSE|1660',  # ITC
    'NSE|1594',  # INFY
    'NSE|11195',  # INDIGO
    'NSE|11723',  # JSWSTEEL
    'NSE|18143',  # JIOFIN
    'NSE|1922',  # KOTAKBANK
    'NSE|11483',  # LT
    'NSE|2031',  # M&M
    'NSE|10999',  # MARUTI
    'NSE|22377',  # MAXHEALTH
    'NSE|11630',  # NTPC
    'NSE|17963',  # NESTLEIND
    'NSE|2475',  # ONGC
    'NSE|14977',  # POWERGRID
    'NSE|2885',  # RELIANCE
    'NSE|21808',  # SBILIFE
    'NSE|4306',  # SHRIRAMFIN
    'NSE|3045',  # SBIN
    'NSE|3351',  # SUNPHARMA
    'NSE|11536',  # TCS
    'NSE|3432',  # TATACONSUM
    'NSE|3456',  # TATA MOTORS PASSENGER VEHICLES
    'NSE|3499',  # TATASTEEL
    'NSE|13538',  # TECHM
    'NSE|3506',  # TITAN
    'NSE|1964',  # TRENT
    'NSE|11532',  # ULTRACEMCO
    'NSE|3787',  # WIPRO
]

# 🔥 CONFIGURATION
TOP_N = 10                    # Execute TOP 10 highest scoring
#TRADE_SCORE = 45             # Minimum score (out of 63pts)
TRADE_SCORE = 1             # Minimum score (out of 63pts)
ENTRY_WEIGHTS = [1.0, 1.0, 1.0, 1.0]
ENTRY_WEIGHTS = [2.0, 1.0, 1.0, 1.0]
MARKET_OPEN = dt_time(9, 15)
MARKET_CLOSE = dt_time(15, 30)
OPTION_EXECUTE = False
OPTION_PRODUCT_TYPE = 'I'
OPTION_PRICE_TYPE = 'MKT'
OPTION_EXPIRY = 'monthly'
OPTION_INSTRUMENT = 'OPTSTK'
HEDGE_STEPS = 4
UPDATE_INTERVAL = 5          # Seconds between scans
VERBOSE_LOGS = False

# 🔥 ABSOLUTE PNL TARGETS (Optional: Set to 0 to disable)
TARGET_PROFIT_RS = 0         # Exit if Total PnL >= this amount (e.g. 5000)
STOP_LOSS_RS = 0             # Exit if Total PnL <= -this amount (e.g. 2500)

# 🔥 PORTFOLIO-WIDE TARGETS (Master Kill-switch)
TOTAL_TARGET_PROFIT_RS = 0   # Exit ALL if Total Session PnL >= this
TOTAL_STOP_LOSS_RS = 0       # Exit ALL if Total Session PnL <= -this

# 🔥 TRAILING SL CONFIG
TSL_RETREACEMENT_PCT = 50    # Exit if Profit falls 50% from peak (Max PnL)
TSL_ACTIVATION_RS = 1000     # Only start retracement trail after ₹1000 profit

SCORE_CAP_ORB_PCT = 0.10
SCORE_CAP_EMA_PCT = 0.10
SCORE_CAP_EMA_CROSS_PCT = 0.10
SIMULATION = False
SCORE_W_ORB_SIZE = 33.0
SCORE_W_ORB_HIGH = 33.0
SCORE_W_ORB_LOW = 34.0
SCORE_SCALE_ORB_SIZE_PCT = 0.05
SCORE_SCALE_ORB_BREAK_PCT = 0.10
SCORE_CAP_ST_PCT = 0.10
SUPER_TREND_PERIOD = 10
SUPER_TREND_MULTIPLIER = 3.0



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
