"""
🚨 SL Filter: Direction-Aware Risk Management
- Options: Exit if premium rises (Loss)
- Futures: Exit if price goes against position (Loss)
"""
from typing import Dict, Any

def check_sl(position: Dict[str, Any], current_ltp: float, data: Dict[str, Any] = None) -> Dict[str, Any]:
    result = {'hit': False, 'pct': 0.0, 'reason': ''}
    try:
        entry_net = position.get('entry_net_premium')
        current_net = data.get('current_net_premium') if data else None
        basis = position.get('atm_premium_entry')
        strategy = position.get('strategy', '')
        is_future = 'FUTURE' in strategy
        
        # 1️⃣ Normalized PnL Check (Handles both Spreads and Futures)
        if entry_net is not None and current_net is not None and basis != 0:
            # Positive = Profit, Negative = Loss
            pct = (entry_net - current_net) / abs(basis) * 100.0
            result['pct'] = pct
            
            # Stop Loss triggers on Negative PCT
            sl_threshold = -10.0 # 10% Loss
            if pct <= sl_threshold:
                result['hit'] = True
                term = "Price Move" if is_future else "Premium Rise"
                result['reason'] = f"Stop Loss: {term} caused {abs(pct):.2f}% drawdown"
            
            # 2️⃣ Cash-based Stop Loss (Priority for Futures)
            total_pnl = pct / 100.0 * abs(basis) * position.get('lot_size', 0)
            sl_rs = position.get('config', {}).get('STOP_LOSS_RS', 0)
            if not result['hit'] and sl_rs > 0 and total_pnl <= -sl_rs:
                result['hit'] = True
                result['reason'] = f"Stop Loss: Cash hit -₹{abs(total_pnl):.2f} <= -₹{sl_rs}"
                
            return result

    except Exception as e:
        result['reason'] = f"error:{e}"
    return result
