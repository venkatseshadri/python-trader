"""TP filter: premium drops >= 10% from entry price (Profit Taking)"""
from typing import Dict, Any

def check_tp(data, candle_data=None, **kwargs) -> Dict[str, Any]:
    """Return dict with {'hit': bool, 'pct': float, 'reason': str}"""
    result = {'hit': False, 'pct': 0.0, 'reason': ''}
    try:
        from orbiter.utils.utils import safe_float
        position = kwargs.get('position', {})
        current_ltp = safe_float(data.get('lp', 0))
        
        # ✅ Priority: Short-Premium based TP
        entry_net = position.get('entry_net_premium')
        current_net = data.get('current_net_premium') if data else None
        basis = position.get('atm_premium_entry') # ✅ Using Short Leg as Basis
        lot_size = position.get('lot_size', 0)
        
        if entry_net is not None and current_net is not None and basis != 0:
            # PnL % relative to the Short Leg value
            pct = (entry_net - current_net) / abs(basis) * 100.0
            result['pct'] = pct
            
            # 1️⃣ Fixed Percentage Check (10% of Short Leg)
            if pct >= 10.0:
                result['hit'] = True
                result['reason'] = f"Profit Target hit: Net Spread decayed {pct:.2f}% of short premium"
            
            # 2️⃣ Total Cash Check (TARGET_PROFIT_RS)
            total_pnl = (entry_net - current_net) * lot_size
            target_profit_rs = position.get('target_profit_rs', 0)
            if not result['hit'] and target_profit_rs > 0 and total_pnl >= target_profit_rs:
                result['hit'] = True
                result['reason'] = f"Profit Target hit: Total PnL ₹{total_pnl:.2f} >= ₹{target_profit_rs}"
                
            return result

        # Fallback: Underlying-based TP (for short positions, underlying dropping is usually good)
        entry = float(position.get('entry_price', 0))
        if entry <= 0 or current_ltp is None:
            return result

        pct = (current_ltp - entry) / entry * 100.0
        result['pct'] = pct
        # For simplicity, assuming short bias for TP if underlying drops
        if pct <= -10.0:
            result['hit'] = True
            result['reason'] = f"Underlying dropped {abs(pct):.2f}% >= 10%"

    except Exception as e:
        result['reason'] = f"error:{e}"

    return result
