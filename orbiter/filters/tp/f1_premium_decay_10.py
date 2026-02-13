"""
🎯 TP Filter: Direction-Aware Profit Booking
- Options: Exit if premium decays (Profit)
- Futures: Exit if price favors position (Profit)
"""
from typing import Dict, Any

def check_tp(position: Dict[str, Any], current_ltp: float, data: Dict[str, Any] = None) -> Dict[str, Any]:
    result = {'hit': False, 'pct': 0.0, 'reason': ''}
    try:
        entry_net = position.get('entry_net_premium')
        current_net = data.get('current_net_premium') if data else None
        basis = position.get('atm_premium_entry')
        strategy = position.get('strategy', '')
        is_future = 'FUTURE' in strategy
        
        if entry_net is not None and current_net is not None and basis != 0:
            # Positive = Profit
            pct = (entry_net - current_net) / abs(basis) * 100.0
            result['pct'] = pct
            
            tp_threshold = 10.0 # 10% Profit
            if pct >= tp_threshold:
                result['hit'] = True
                term = "Price appreciation" if is_future else "Premium decay"
                result['reason'] = f"Take Profit: {term} reached {pct:.2f}%"
            
            # Cash-based Target
            total_pnl = pct / 100.0 * abs(basis) * position.get('lot_size', 0)
            tp_rs = position.get('config', {}).get('TARGET_PROFIT_RS', 0)
            if not result['hit'] and tp_rs > 0 and total_pnl >= tp_rs:
                result['hit'] = True
                result['reason'] = f"Take Profit: Cash target ₹{total_pnl:.2f} >= ₹{tp_rs}"
                
            return result

    except Exception as e:
        result['reason'] = f"error:{e}"
    return result
