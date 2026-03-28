#!/usr/bin/env python3
"""
Quick Health Check - Lightweight version for frequent checks
"""

import os
import sys
import json
import subprocess
from datetime import datetime

CONFIG = {
    "tmp_dir": "/tmp",
    "data_dir": "/home/trading_ceo/python-trader/orbiter/data",
    "binary_path": "/home/trading_ceo/python-trader/dist/orbiter-4.6.1",
}

def quick_check():
    """Quick health check - returns exit code 0 if healthy, 1 if issues."""
    issues = []
    
    # Check binary exists
    if not os.path.exists(CONFIG["binary_path"]):
        issues.append(f"Binary missing: {CONFIG['binary_path']}")
    
    # Check recent log activity (last 6 hours)
    for strat in ["n1", "n2", "s1", "s2", "m1"]:
        log_path = os.path.join(CONFIG["tmp_dir"], f"orbiter_{strat}.log")
        if os.path.exists(log_path):
            age_minutes = (os.path.getmtime(log_path) - os.path.getctime(log_path)) / 60
            # Check file was modified recently (within 6 hours)
            import time
            if time.time() - os.path.getmtime(log_path) > 6 * 3600:
                issues.append(f"{strat}: No recent activity")
    
    # Check paper positions
    pp_path = os.path.join(CONFIG["data_dir"], "paper_positions.json")
    if os.path.exists(pp_path):
        try:
            with open(pp_path) as f:
                json.load(f)
        except:
            issues.append("paper_positions.json corrupted")
    
    if issues:
        print("⚠️ Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return 1
    
    print("✅ All systems operational")
    return 0

if __name__ == "__main__":
    sys.exit(quick_check())
