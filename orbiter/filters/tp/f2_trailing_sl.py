"""TP filter: Trailing SL logic
- Enable trail SL once post 5% drop (profit)
- Increase SL by 1% when the profit % increases by 1%
"""
from typing import Dict, Any

def check_trailing_sl(position: Dict[str, Any], current_ltp: float, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Return dict with {'hit': bool, 'pct': float, 'reason': str}"""
    result = {'hit': False, 'pct': 0.0, 'reason': ''}
    try:
        max_profit = position.get('max_profit_pct', 0.0)
        entry_net = position.get('entry_net_premium', 0)
        current_net = data.get('current_net_premium') if data else None
        
        if entry_net == 0 or current_net is None:
            return result

        # 1. Check if we have reached the 5% threshold to start trailing
        if max_profit < 5.0:
            return result

        # 2. Calculate current Trailed SL Level (in terms of profit %)
        # "Increase SL by 1% when profit increases by 1%" starting from 5%
        # At 5% profit, Trailed SL = 0% (Break-even)
        # At 10% profit, Trailed SL = 5%
        trailed_sl_profit_pct = max_profit - 5.0
        
        # 3. Calculate Current Profit % (Relative to Short Premium)
        basis = position.get('atm_premium_entry', 0)
        current_profit_pct = (entry_net - current_net) / abs(basis) * 100.0 if basis != 0 else 0
        result['pct'] = current_profit_pct
        
        # 4. Check if current profit has dropped back to hit the trailed SL
        if current_profit_pct <= trailed_sl_profit_pct:
            result['hit'] = True
            result['reason'] = f"Trailing SL hit: Max Profit reached {max_profit:.2f}%, exited at {current_profit_pct:.2f}% (Locked {trailed_sl_profit_pct:.2f}%)"

    except Exception as e:
        result['reason'] = f"error:{e}"

    return result
