"""TP filter: Trailing SL logic
- Enable trail SL once post 5% drop (profit)
- Increase SL by 1% when the profit % increases by 1%
"""
from typing import Dict, Any

def check_trailing_sl(position: Dict[str, Any], current_ltp: float, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Profit Guard Pro: Tight trailing for leveraged Credit Spreads"""
    result = {'hit': False, 'pct': 0.0, 'reason': ''}
    try:
        max_profit = position.get('max_profit_pct', 0.0)
        entry_net = position.get('entry_net_premium', 0)
        current_net = data.get('current_net_premium') if data else None
        
        if entry_net == 0 or current_net is None:
            return result

        # 1. Activation: Start trailing early (1.5% profit)
        activation_threshold = position.get('tp_trail_activation', 1.5)
        if max_profit < activation_threshold:
            return result

        # 2. Dynamic SL Calculation
        # Gap is now tight (0.75%)
        trail_gap = position.get('tp_trail_gap', 0.75)
        trailed_sl_profit_pct = max_profit - trail_gap
        
        # 3. Peak-Lock: If we reached > 3% profit, never let it go below 1%
        if max_profit >= 3.0:
            trailed_sl_profit_pct = max(trailed_sl_profit_pct, 1.0)

        # 4. Calculate Current Profit % (Relative to Short Premium)
        basis = position.get('atm_premium_entry', 0)
        current_profit_pct = (entry_net - current_net) / abs(basis) * 100.0 if basis != 0 else 0
        result['pct'] = current_profit_pct
        
        # 5. Check for hit
        if current_profit_pct <= trailed_sl_profit_pct:
            result['hit'] = True
            result['reason'] = f"Profit Guard Pro hit: Max {max_profit:.2f}%, Trail-Floor {trailed_sl_profit_pct:.2f}%"

    except Exception as e:
        result['reason'] = f"error:{e}"

    return result
