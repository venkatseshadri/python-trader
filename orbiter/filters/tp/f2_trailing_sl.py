"""
📈 TP Filter: Trailing SL logic
- Works for both Options (Trailing Decay) and Futures (Trailing Price)
"""
from typing import Dict, Any

def check_trailing_sl(position: Dict[str, Any], current_ltp: float, data: Dict[str, Any] = None) -> Dict[str, Any]:
    result = {'hit': False, 'pct': 0.0, 'reason': ''}
    try:
        max_profit = position.get('max_profit_pct', 0.0)
        entry_net = position.get('entry_net_premium', 0)
        current_net = data.get('current_net_premium') if data else None
        basis = position.get('atm_premium_entry', 0)
        strategy = position.get('strategy', '')
        is_future = 'FUTURE' in strategy
        
        if entry_net == 0 or current_net is None or basis == 0:
            return result

        # Enable trail SL once post 5% profit
        if max_profit < 5.0:
            return result

        # Locked profit = Max Profit - 5% buffer
        trailed_sl_profit_pct = max_profit - 5.0
        
        # Current profit % (Normalized)
        current_profit_pct = (entry_net - current_net) / abs(basis) * 100.0
        result['pct'] = current_profit_pct
        
        if current_profit_pct <= trailed_sl_profit_pct:
            result['hit'] = True
            term = "Price retraced" if is_future else "Premium rose back"
            result['reason'] = f"Trailing SL: {term} after {max_profit:.2f}% peak (Closed @ {current_profit_pct:.2f}%)"

    except Exception as e:
        result['reason'] = f"error:{e}"
    return result
