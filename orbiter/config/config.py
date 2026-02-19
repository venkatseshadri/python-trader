from datetime import time as dt_time

# 🔥 SHARED CONFIGURATION
TOP_N = 10                    # Execute TOP 10 highest scoring
TRADE_SCORE = 0.50            # Trigger on 0.5% ORB move

ENTRY_WEIGHTS = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

OPTION_EXECUTE = False
OPTION_PRODUCT_TYPE = 'I'
OPTION_PRICE_TYPE = 'MKT'
OPTION_EXPIRY = 'monthly'
HEDGE_STEPS = 4
UPDATE_INTERVAL = 5          # Seconds between scans
VERBOSE_LOGS = True

# 🔥 ABSOLUTE PNL TARGETS (Optional: Set to 0 to disable)
TARGET_PROFIT_RS = 0         # Exit if Total PnL >= this amount
STOP_LOSS_RS = 0             # Exit if Total PnL <= -this amount

# 🔥 PORTFOLIO-WIDE TARGETS (Master Kill-switch)
TOTAL_TARGET_PROFIT_RS = 0   
TOTAL_STOP_LOSS_RS = 0       

# 🔥 TRAILING SL CONFIG
TSL_RETREACEMENT_PCT = 40    
TSL_ACTIVATION_RS = 1000     

SCORE_CAP_ORB_PCT = 0.10
SCORE_CAP_EMA_PCT = 0.10
SCORE_CAP_EMA_CROSS_PCT = 0.10
SCORE_W_ORB_SIZE = 33.0
SCORE_W_ORB_HIGH = 33.0
SCORE_W_ORB_LOW = 34.0
SCORE_SCALE_ORB_SIZE_PCT = 0.05
SCORE_SCALE_ORB_BREAK_PCT = 0.10
SCORE_CAP_ST_PCT = 0.10
SUPER_TREND_PERIOD = 10
SUPER_TREND_MULTIPLIER = 3.0
