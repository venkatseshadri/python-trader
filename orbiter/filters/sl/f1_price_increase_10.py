"""SL filter: premium rises >= 10% from entry price"""
from typing import Dict, Any

def check_sl(position: Dict[str, Any], current_ltp: float, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Return dict with {'hit': bool, 'pct': float, 'reason': str}"""
    result = {'hit': False, 'pct': 0.0, 'reason': ''}
    try:
        # ✅ Priority: Short-Premium based SL
        entry_net = position.get('entry_net_premium')
        current_net = data.get('current_net_premium') if data else None
        basis = position.get('atm_premium_entry') # ✅ Using Short Leg as Basis
        lot_size = position.get('lot_size', 0)
        
        if entry_net is not None and current_net is not None and basis != 0:
            # PnL % relative to the Short Leg value
            pct = (entry_net - current_net) / abs(basis) * 100.0
            result['pct'] = pct
            
            # 1️⃣ Fixed Percentage Check (10% of Short Leg)
            if pct <= -10.0:
                result['hit'] = True
                result['reason'] = f"Stop Loss hit: Net Spread rose {abs(pct):.2f}% of short premium"
            
            # 2️⃣ Total Cash Check (STOP_LOSS_RS)
            total_pnl = (entry_net - current_net) * lot_size
            stop_loss_rs = position.get('stop_loss_rs', 0)
            if not result['hit'] and stop_loss_rs > 0 and total_pnl <= -stop_loss_rs:
                result['hit'] = True
                result['reason'] = f"Stop Loss hit: Total PnL -₹{abs(total_pnl):.2f} <= -₹{stop_loss_rs}"
                
            return result

        # Fallback: Underlying-based SL
        entry = float(position.get('entry_price', 0))
        if entry <= 0 or current_ltp is None:
            return result

        pct = (current_ltp - entry) / entry * 100.0
        result['pct'] = pct
        # Premium-based SL: trigger when price rises by 10% or more
        if pct >= 10.0:
            result['hit'] = True
            result['reason'] = f"Underlying rose {pct:.2f}% >= +10% SL"

    except Exception as e:
        result['reason'] = f"error:{e}"

    return result
