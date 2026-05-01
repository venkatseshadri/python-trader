#!/usr/bin/env python3
"""
Market Hours & Holiday Utilities

Provides shared utilities for Varaha and Kurma trading bots to:
- Check if today is a market holiday
- Check if it's a weekend
- Prevent trading on non-trading days
"""

import json
from datetime import datetime
from pathlib import Path


def is_weekend():
    """Check if today is Saturday (5) or Sunday (6)"""
    return datetime.now().weekday() >= 5


def is_market_holiday():
    """Check if today is an Indian market holiday"""
    today = datetime.now().strftime("%Y-%m-%d")

    # Try to load holidays from research config
    holidays_file = Path("/root/.picoclaw/workspace/config/market_holidays.json")

    if holidays_file.exists():
        try:
            with open(holidays_file) as f:
                config = json.load(f)
            holiday_dates = [h["date"] for h in config.get("holidays", [])]
            return today in holiday_dates
        except (json.JSONDecodeError, KeyError):
            pass

    return False


def is_market_open():
    """
    Check if Indian markets are open today

    Returns:
        bool: True if markets are open (weekday + not holiday), False otherwise
    """
    return not is_weekend() and not is_market_holiday()


def get_market_status():
    """
    Get detailed market status

    Returns:
        dict: {
            'is_open': bool,
            'is_weekend': bool,
            'is_holiday': bool,
            'date': str (YYYY-MM-DD),
            'day_name': str
        }
    """
    now = datetime.now()
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    is_wknd = is_weekend()
    is_hol = is_market_holiday()

    return {
        'is_open': not is_wknd and not is_hol,
        'is_weekend': is_wknd,
        'is_holiday': is_hol,
        'date': now.strftime("%Y-%m-%d"),
        'day_name': day_names[now.weekday()]
    }


if __name__ == "__main__":
    # Quick test
    status = get_market_status()
    print(f"Date: {status['date']} ({status['day_name']})")
    print(f"Market Open: {status['is_open']}")
    print(f"Is Weekend: {status['is_weekend']}")
    print(f"Is Holiday: {status['is_holiday']}")
