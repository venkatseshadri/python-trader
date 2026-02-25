"""TP filter: Trailing SL logic
- Enable trail SL once post 5% drop (profit)
- Increase SL by 1% when the profit % increases by 1%
"""
from typing import Dict, Any

def check_trailing_sl(data, candle_data=None, **kwargs) -> Dict[str, Any]:
    """Profit Guard Pro (V2): Trailing based on hard Cash PnL (₹)"""
    result = {'hit': False, 'pct': 0.0, 'reason': ''}
    try:
        from orbiter.utils.utils import safe_float
        position = kwargs.get('position', {})
        # ✅ Get values from the position dict
        max_pnl_rs = position.get('max_pnl_rs', 0.0)
        current_pnl_rs = position.get('pnl_rs', 0.0) # Calculated in Executor
        
        # 1. Activation: Only start trailing once we hit a Rupee milestone
        # Default: 1% of Notional or a fixed ₹1000
        activation_rs = position.get('tsl_activation_rs', 1000)
        if max_pnl_rs < activation_rs:
            return result

        # 2. Trailing Gap (In Rupees)
        # We use a % of the Max PnL reached as the 'allowed give-back'
        # Default: 40% retracement allowed (e.g., if you make ₹1000, you exit at ₹600)
        retracement_pct = position.get('tsl_retracement_pct', 40)
        allowed_drop = max_pnl_rs * (retracement_pct / 100.0)
        trail_floor_rs = max_pnl_rs - allowed_drop
        
        # 3. Floor-Lock: Once we've made good money, never let it go red
        # If Peak PnL > ₹2000, floor must be at least ₹500
        if max_pnl_rs >= 2000:
            trail_floor_rs = max(trail_floor_rs, 500.0)

        # 4. Check for hit
        if current_pnl_rs <= trail_floor_rs:
            result['hit'] = True
            result['pct'] = (current_pnl_rs / position.get('entry_price', 1)) # Dummy for logging
            result['reason'] = (f"Cash TSL Hit: Peak ₹{max_pnl_rs:.0f}, "
                               f"Floor ₹{trail_floor_rs:.0f}, Current ₹{current_pnl_rs:.0f}")

    except Exception as e:
        result['reason'] = f"error:{e}"

    return result
