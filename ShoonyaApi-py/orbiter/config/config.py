"""
ORBITER CONFIG: NIFTY 50 F&O STOCKS ONLY (All have active F&O contracts)
"""

# 🔥 STANDARD NIFTY 50 F&O TOKENS (Confirmed Shoonya NSE tokens)
SYMBOLS_UNIVERSE = [
    # BANKING & FINANCE (F&O Active)
    'NSE|1333',    # HDFCBANK-EQ
    'NSE|3045',    # SBIN-EQ
    'NSE|317',     # BAJFINANCE-EQ
    'NSE|526',     # AXISBANK-EQ
    'NSE|500696',  # INDUSINDBK-EQ
    'NSE|500285',  # KOTAKBANK-EQ
    
    # ENERGY & OIL (F&O Active)
    'NSE|2885',    # RELIANCE-EQ  
    'NSE|11630',   # NTPC-EQ
    'NSE|2475',    # ONGC-EQ
    'NSE|500312',  # BPCL-EQ
    
    # METALS & STEEL (F&O Active)
    'NSE|500472',  # TATASTEEL-EQ
    'NSE|500820',  # JSWSTEEL-EQ
    
    # IT & TECH (F&O Active)
    'NSE|500875',  # INFY-EQ
    'NSE|500790',  # WIPRO-EQ
    'NSE|500180',  # HCLTECH-EQ
    'NSE|19681',   # TECHM-EQ
    
    # AUTO (F&O Active)
    'NSE|570',     # MARUTI-EQ
    'NSE|500770',  # TATAMOTORS-EQ
    'NSE|500209',  # HEROMOTOCO-EQ
    
    # FMCG (F&O Active)
    'NSE|1394',    # HINDUNILVR-EQ
    'NSE|1660',    # ITC-EQ
    'NSE|500112',  # NESTLEIND-EQ
    
    # CONSTRUCTION & INFRA (F&O Active)
    'NSE|500295',  # LT-EQ
    'NSE|5425',    # POWERGRID-EQ
    
    # PHARMA (F&O Active)
    'NSE|53231',   # CIPLA-EQ
    'NSE|500124',  # DRREDDY-EQ
    
    # OTHERS (All F&O Active)
    'NSE|500',     # BHARTIARTL-EQ
    'NSE|90',      # ASIANPAINT-EQ
    'NSE|500510',  # HINDALCO-EQ
    'NSE|500660',  # GRASIM-EQ
    'NSE|500300',  # TITAN-EQ
    'NSE|500020',  # EICHERMOT-EQ
    'NSE|532540',  # COALINDIA-EQ
    'NSE|500247',  # DIVISLAB-EQ
]

# 🔥 CONFIGURATION
TOP_N = 7                    # Execute TOP 7 highest scoring
TRADE_SCORE = 45             # Minimum score (out of 63pts)
UPDATE_INTERVAL = 5          # Seconds between scans

# 🔥 F&O ORB BREAKOUT LEVELS (Adjust based on market)
ORB_LEVELS = {
    'NSE|2885': 1450,        # RELIANCE
    'NSE|11630': 360,        # NTPC
    'NSE|317': 7000,         # BAJFINANCE
    'NSE|3045': 800,         # SBIN
    'NSE|1333': 1600,        # HDFCBANK
    'NSE|1660': 500,         # ITC
    'NSE|1394': 2600,        # HINDUNILVR
    'NSE|500875': 1800,      # INFY
    'NSE|570': 12500,        # MARUTI
    'NSE|500295': 3600,      # LT
}

print(f"🚀 NIFTY 50 F&O Universe: {len(SYMBOLS_UNIVERSE)} stocks")
print(f"📈 TOP {TOP_N} execution | Min score: {TRADE_SCORE}pts")
