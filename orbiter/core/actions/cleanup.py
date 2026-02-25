# orbiter/core/actions/cleanup.py

import logging
from typing import Dict, Any

logger = logging.getLogger("ORBITER")

def square_off_all_positions(state: Any, reason: str = "SYSTEM_REQUEST"):
    """
    Squares off all active positions in the system.
    This logic was originally in the old Executor class.
    """
    if not state.active_positions: return []
    to_square = []
    exec_orders = state.config.get('OPTION_EXECUTE', False) # This is still hardcoded config!

    for token, info in list(state.active_positions.items()):
        ltp = state.client.get_ltp(token) or info.get('entry_price', 0)
        strategy = info.get('strategy', '')
        
        # Handle Future Square-Off
        if 'FUTURE' in strategy:
            if exec_orders:
                side = 'S' if 'LONG' in strategy else 'B'
                qty = info.get('lot_size', 0)
                exch = token.split('|')[0] if '|' in token else 'NFO'
                tsym = state.client.TOKEN_TO_SYMBOL.get(token.split('|')[-1])
                if qty > 0 and tsym:
                    p_type = state.config.get('OPTION_PRICE_TYPE', 'MKT')
                    fut_exit_p = 0
                    if 'NIFTY' in tsym.upper(): p_type = 'MKT'
                    elif p_type == 'LMT':
                        if side == 'B': fut_exit_p = round(float(ltp) * 1.01, 1)
                        else: fut_exit_p = round(float(ltp) * 0.99, 1)

                    state.client.api.place_order(buy_or_sell=side, product_type=state.config.get('OPTION_PRODUCT_TYPE'),
                                               exchange=exch, tradingsymbol=tsym, quantity=qty, discloseqty=0,
                                               price_type=p_type, price=fut_exit_p, retention='DAY', remarks=f'{reason}_sq_fut')
            # ... (rest of logging logic)

        # Handle Spread Square-Off
        else:
            atm_p_exit = state.client.get_option_ltp_by_symbol(info.get('atm_symbol'))
            hdg_p_exit = state.client.get_option_ltp_by_symbol(info.get('hedge_symbol'))

            if exec_orders:
                qty, atm_s, hdg_s = info.get('lot_size', 0), info.get('atm_symbol'), info.get('hedge_symbol')
                if qty > 0 and atm_s and hdg_s:
                    p_type = state.config.get('OPTION_PRICE_TYPE', 'MKT')
                    atm_exit_p, hdg_exit_p = 0, 0
                    if 'NIFTY' in atm_s.upper(): p_type = 'MKT'
                    elif p_type == 'LMT':
                        atm_exit_p = round((atm_p_exit or 0) * 1.02, 1)
                        hdg_exit_p = round((hdg_p_exit or 0) * 0.98, 1)

                    state.client.api.place_order(buy_or_sell='B', product_type=state.config.get('OPTION_PRODUCT_TYPE'),
                                               exchange='NFO', tradingsymbol=atm_s, quantity=qty, discloseqty=0,
                                               price_type=p_type, price=atm_exit_p, retention='DAY', remarks=f'{reason}_sq_atm')
                    
                    # ... (rest of square-off logic)
