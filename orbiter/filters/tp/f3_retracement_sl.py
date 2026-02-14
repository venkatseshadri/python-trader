"""TP filter: PnL Retracement Trailing SL
- Triggers if current PnL falls X% below the peak PnL (Max PnL) reached.
- Only activates if profit is above a minimum threshold (e.g., ₹500) to avoid noise.
"""
from typing import Dict, Any

def check_retracement_sl(position: Dict[str, Any], current_ltp: float, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Return dict with {'hit': bool, 'pct': float, 'reason': str}"""
    result = {'hit': False, 'pct': 0.0, 'reason': ''}
    try:
        max_pnl = position.get('max_pnl_rs', 0.0)
        entry_net = position.get('entry_net_premium', 0)
        current_net = data.get('current_net_premium') if data else None
        lot_size = position.get('lot_size', 0)
        config_obj = position.get('config', {})
        retracement_pct = config_obj.get('TSL_RETREACEMENT_PCT', 50)
        activation_rs = config_obj.get('TSL_ACTIVATION_RS', 1000)
        
        if entry_net == 0 or current_net is None or lot_size == 0:
            return result

        # Current Cash PnL
        current_pnl = (entry_net - current_net) * lot_size
        
        # 1. Activation Threshold: Only trail if we have made at least the configured profit
        if max_pnl < activation_rs:
            return result

        # 2. Calculate allowed drop from peak
        allowed_drop = max_pnl * (retracement_pct / 100.0)
        exit_threshold = max_pnl - allowed_drop
        
        # 3. Check for hit
        if current_pnl < exit_threshold:
            result['hit'] = True
            result['reason'] = (f"PnL Retracement hit: Peak was ₹{max_pnl:.2f}, "
                               f"trailed {retracement_pct}% to ₹{exit_threshold:.2f}. "
                               f"Current PnL ₹{current_pnl:.2f}")

    except Exception as e:
        result['reason'] = f"error:{e}"

    return result
