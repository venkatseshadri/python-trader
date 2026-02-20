"""SL filter: Smart ATR-based Volatility Stop Loss
- For Spreads: Exit if premium rises > (Entry + ATR * 0.25)
- For Futures: Exit if price breaks (Entry +/- ATR * 1.5)
"""
from typing import Dict, Any

def check_sl(position: Dict[str, Any], current_ltp: float, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Return dict with {'hit': bool, 'pct': float, 'reason': str}"""
    result = {'hit': False, 'pct': 0.0, 'reason': ''}
    try:
        strategy = position.get('strategy', '')
        entry_price = float(position.get('entry_price', 0))
        entry_atr = float(position.get('entry_atr', 0))
        mult = float(position.get('atr_sl_mult', 1.5))
        
        # 1. Total Cash SL Check (Highest Priority)
        entry_net = position.get('entry_net_premium')
        current_net = data.get('current_net_premium') if data else None
        lot_size = position.get('lot_size', 0)
        stop_loss_rs = position.get('stop_loss_rs', 0)

        if entry_net is not None and current_net is not None and lot_size > 0:
            total_pnl = (entry_net - current_net) * lot_size
            if stop_loss_rs > 0 and total_pnl <= -stop_loss_rs:
                result['hit'] = True
                result['reason'] = f"Hard SL: Total PnL ₹{total_pnl:.2f} <= ₹-{stop_loss_rs}"
                return result

        # 2. ATR-Based Volatility Stop
        if entry_atr > 0:
            # ✅ Handle SPREADS
            if 'CREDIT_SPREAD' in strategy and entry_net is not None and current_net is not None:
                # Premium Buffer = ATR * 0.25 (as per Oct 2024 Research)
                sl_threshold_premium = entry_net + (entry_atr * mult)
                if current_net >= sl_threshold_premium:
                    result['hit'] = True
                    result['reason'] = f"Smart ATR SL: Premium {current_net:.2f} > Threshold {sl_threshold_premium:.2f} (ATR: {entry_atr:.2f})"
            
            # ✅ Handle FUTURES
            elif 'FUTURE' in strategy:
                # Price Buffer = ATR * 1.5
                if 'LONG' in strategy:
                    sl_price = entry_price - (entry_atr * mult)
                    if current_ltp <= sl_price:
                        result['hit'] = True
                        result['reason'] = f"Smart ATR SL: LTP {current_ltp:.2f} <= SL {sl_price:.2f} (ATR: {entry_atr:.2f})"
                else: # SHORT
                    sl_price = entry_price + (entry_atr * mult)
                    if current_ltp >= sl_price:
                        result['hit'] = True
                        result['reason'] = f"Smart ATR SL: LTP {current_ltp:.2f} >= SL {sl_price:.2f} (ATR: {entry_atr:.2f})"

    except Exception as e:
        result['reason'] = f"error:{e}"

    return result
