from datetime import time as dt_time

# 🔥 SHARED CONFIGURATION
TOP_N = 1                    # 🔥 NIFTY SPRINT: Only 1 Trade at a time
TRADE_SCORE = 0.40            # Aggressive entry for Power Hour

ENTRY_WEIGHTS = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

OPTION_EXECUTE = True        # 🔥 LIVE EXECUTION ACTIVE
OPTION_PRODUCT_TYPE = 'I'
OPTION_PRICE_TYPE = 'MKT'
OPTION_EXPIRY = 'weekly'     # 🔥 Focus on NIFTY weekly expiry
HEDGE_STEPS = 4
UPDATE_INTERVAL = 5          # Seconds between scans
VERBOSE_LOGS = True

# 🔥 ABSOLUTE PNL TARGETS (Optional: Set to 0 to disable)
TARGET_PROFIT_RS = 0         # Exit if Total PnL >= this amount
STOP_LOSS_RS = 0             # Exit if Total PnL <= -this amount

# 🔥 PORTFOLIO-WIDE TARGETS (Master Kill-switch)
TOTAL_TARGET_PROFIT_RS = 1100   # 🔥 VPS Fund Target (v3.16.0)
TOTAL_STOP_LOSS_RS = 5000       # Hard Stop (User Mandate)
GLOBAL_TSL_ENABLED = False      # 🔥 Disable trailing for immediate ₹1100 lock-in
GLOBAL_TSL_PCT = 20             # 20% Retracement (Research Optimized)

# 🔥 TRAILING SL CONFIG
TSL_RETREACEMENT_PCT = 40    
TSL_ACTIVATION_RS = 500     

# 🔥 STRATEGY MULTIPLIERS (v3.14.0)
SL_MULT_TRENDING = 1.5
SL_MULT_SIDEWAYS = 0.25

# 🔥 ASSET FILTERING (v3.14.1)
MAX_NOMINAL_PRICE = 30000    # 🔥 Lifted to allow NIFTY (v3.15.2)
FUTURE_MAX_LOSS_PCT = 5.0    # 5% Max tolerance on nominal value (v3.14.5)

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
