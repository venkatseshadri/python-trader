# Margin Checker Integration for Orbiter
# This module provides margin checking before trade execution

import os
import sys
import json
from datetime import datetime
from typing import Dict, Optional

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .margin_checker import MarginChecker, PaperTradeSimulator

# Default config for paper trading
PAPER_CONFIG = {
    "paper_trade": {
        "initial_capital": 100000,
        "cash": 100000,
        "used_margin": 0,
        "mtm": 0,
        "positions": []
    },
    "trading_rules": {
        "max_daily_loss": 5000,
        "warning_at": -4000,
        "profit_lock_at": 5000,
        "risk_after_profit": 2500,
        "per_trade_sl": 2500,
        "cooling_off_minutes": 30
    }
}

MARGIN_CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'margin_config.json')

def get_checker(paper_trade: bool = True) -> MarginChecker:
    """Get margin checker instance."""
    return MarginChecker(paper_trade=paper_trade)

def check_before_trade(symbol: str, qty: int = 1, premium: float = 0, paper_trade: bool = True) -> Dict:
    """
    Check if trade is allowed based on margin.
    
    Returns:
        dict with keys: allowed (bool), reason (str), available (float), required (float)
    """
    checker = get_checker(paper_trade)
    result = checker.check_margin_for_trade(symbol, qty, premium)
    
    # Log the check
    log_file = os.path.join(os.path.dirname(__file__), 'margin_log.txt')
    with open(log_file, 'a') as f:
        f.write(f"[{datetime.now().isoformat()}] MARGIN CHECK: {symbol} {qty} - {'ALLOWED' if result['allowed'] else 'BLOCKED'}\n")
        f.write(f"  Available: Rs{result.get('available', 0):,.0f}, Required: Rs{result.get('required', 0):,.0f}\n")
        if not result['allowed']:
            f.write(f"  Reason: {result.get('reason', 'N/A')}\n")
    
    return result

def record_paper_trade(symbol: str, qty: int, price: float, trade_type: str):
    """Record a paper trade and track margin."""
    checker = get_checker(paper_trade=True)
    checker.record_trade(symbol, qty, price, trade_type)

def get_margin_status() -> Dict:
    """Get current margin status."""
    checker = get_checker(paper_trade=True)
    return checker.get_limits()

def get_paper_positions() -> list:
    """Get open paper positions."""
    sim = PaperTradeSimulator.load_state()
    return sim.positions

# Auto-initialize if needed
def ensure_initialized():
    """Ensure paper trade state is initialized."""
    state_file = os.path.join(os.path.dirname(__file__), 'paper_trade_state.json')
    if not os.path.exists(state_file):
        sim = PaperTradeSimulator(PAPER_CONFIG['paper_trade'])
        sim._save_state()
        print(f"[MARGIN] Initialized paper trade with Rs1,00,000")

# Initialize on import
ensure_initialized()
