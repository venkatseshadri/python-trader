"""
ORBITER Framework Configuration
===============================

Single file controls:
- Universe (NIFTY50)
- Strategy selection  
- Risk parameters
- Broker settings
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
import yaml

# =============================================================================
# BROKER SETTINGS
# =============================================================================

BROKER = {
    "exchange_equity": "NSE",
    "exchange_fno": "NFO",
    "cred_path": "cred.yml",
    "simulate": True,  # Set False for LIVE trading
}

# =============================================================================
# UNIVERSE - Full NIFTY50 (will be filtered to Top-10 by strategy)
# =============================================================================

NIFTY50_SYMBOLS = [
    "RELIANCE-EQ", "HDFCBANK-EQ", "ICICIBANK-EQ", "INFY-EQ", "TCS-EQ",
    "ITC-EQ", "KOTAKBANK-EQ", "LT-EQ", "HINDUNILVR-EQ", "SBIN-EQ",
    "AXISBANK-EQ", "BAJFINANCE-EQ", "BHARTIARTL-EQ", "MARUTI-EQ", "HCLTECH-EQ",
    "SUNPHARMA-EQ", "TITAN-EQ", "ASIANPAINT-EQ", "NESTLEIND-EQ", "ULTRACEMCO-EQ",
    "NTPC-EQ", "POWERGRID-EQ", "TECHM-EQ", "ONGC-EQ", "TATACONSUM-EQ",
    "WIPRO-EQ", "JSWSTEEL-EQ", "COALINDIA-EQ", "DIVISLAB-EQ", "GRASIM-EQ",
    "DRREDDY-EQ", "CIPLA-EQ", "HEROMOTOCO-EQ", "APOLLOHOSP-EQ", "EICHERMOT-EQ",
    "HDFCLIFE-EQ", "BRITANNIA-EQ", "LTIM-EQ", "SHRIRAMFIN-EQ", "BAJAJFINSV-EQ",
    "BPCL-EQ", "TATAMOTORS-EQ", "ADANIPORTS-EQ", "TATASTEEL-EQ", "INDUSINDBK-EQ",
    "M&M-EQ", "TRIDENT-EQ", "BAJAJ-AUTO-EQ"
]

UNIVERSE = {
    "symbols": NIFTY50_SYMBOLS,
}

# =============================================================================
# STRATEGY REGISTRY - Change STRATEGY_NAME only to switch strategies
# =============================================================================

STRATEGY_NAME = "ORB_NIFTY50_TOP10"

STRATEGIES = {
    "ORB_NIFTY50_TOP10": {
        "module": "orb_strategy",
        "class": "ORBStrategy",
        "params": {
            # ORB Window
            "orb_start": "09:15",
            "orb_end": "09:30",
            
            # Selection
            "top_n": 10,                    # Top N strongest ORB among 50
            
            # Risk Management
            "option_sl_pct": 0.30,          # 30% SL on option premium
            "option_target_pct": 0.50,      # 50% target (optional)
            
            # Options
            "expiry_type": "CURRENT_WEEK",  # CURRENT_WEEK, NEXT_WEEK, MONTHLY
            "strike_offset_ce": 50,         # ATM + 50 for CE
            "strike_offset_pe": -50,        # ATM - 50 for PE
            "default_lot_size": 25,
            
            # Minimum filters
            "min_orb_distance_pct": 0.1,    # 0.1% minimum breakout distance
        },
    },
}

# =============================================================================
# LOGGING
# =============================================================================

LOGGING = {
    "log_file": "logs/orbiter.log",
    "log_level": "INFO",
}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def ensure_dirs():
    """Create required directories."""
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)

def load_credentials():
    """Load Shoonya credentials from cred.yml"""
    cred_path = Path(BROKER["cred_path"])
    if not cred_path.exists():
        raise FileNotFoundError(f"Missing {cred_path}. Copy cred.yml.example.")
    
    with open(cred_path) as f:
        return yaml.safe_load(f)

def get_strategy_config():
    """Get active strategy configuration."""
    if STRATEGY_NAME not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {STRATEGY_NAME}")
    return STRATEGIES[STRATEGY_NAME]

# =============================================================================
# STANDALONE TEST BLOCK - Fully self-contained
# =============================================================================

if __name__ == "__main__":
    # Create directories
    ensure_dirs()
    
    print("✅ ORBITER Config OK")
    print(f"   Strategy: {STRATEGY_NAME}")
    print(f"   Universe: {len(UNIVERSE['symbols'])} symbols")
    print(f"   Simulate: {BROKER['simulate']}")
    print(f"   Top N: {STRATEGIES[STRATEGY_NAME]['params']['top_n']}")
    print(f"   Creds: {'❌ Missing (OK for test)' if not Path('cred.yml').exists() else '✅ Found'}")