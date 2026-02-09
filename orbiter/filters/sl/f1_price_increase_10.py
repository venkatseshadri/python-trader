"""SL filter: premium rises >= 10% from entry price"""
from typing import Dict, Any

def check_sl(position: Dict[str, Any], current_ltp: float) -> Dict[str, Any]:
    """Return dict with {'hit': bool, 'pct': float, 'reason': str}

    position: {'entry_price': float, 'entry_time': ..., 'symbol': ..., 'company_name': ...}
    current_ltp: latest market price
    """
    result = {'hit': False, 'pct': 0.0, 'reason': ''}
    try:
        entry = float(position.get('entry_price', 0))
        if entry <= 0 or current_ltp is None:
            return result

        pct = (current_ltp - entry) / entry * 100.0
        result['pct'] = pct
        # Premium-based SL: trigger when price rises by 10% or more
        if pct >= 10.0:
            result['hit'] = True
            result['reason'] = f"Premium rose {pct:.2f}% >= +10% SL"

    except Exception as e:
        result['reason'] = f"error:{e}"

    return result
