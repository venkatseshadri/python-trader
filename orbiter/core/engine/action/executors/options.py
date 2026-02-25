# orbiter/core/engine/action/executors/options.py

from .base import BaseActionExecutor
from typing import Dict, Any
import logging

class OptionActionExecutor(BaseActionExecutor):
    def execute(self, **params: Dict) -> Any:
        symbol = params.get('symbol', 'NIFTY')
        option_type = params.get('option') # CE or PE
        strike_logic = params.get('strike') # ATM, ATM+2, etc
        side = params.get('side', 'B').upper()
        
        # 1. Resolve Underlying Exchange & LTP
        # Default: Use the segment's primary exchange (NSE for NFO, MCX for MCX)
        primary_exch = 'MCX' if self.state.client.segment_name == 'mcx' else 'NSE'
        exch = params.get('exchange', primary_exch)
        token = self.state.client.get_token(symbol)
        
        ltp = self.state.client.get_ltp(f"{exch}|{token}")
        if not ltp:
            # Fallback if specific exch|token not in live feed (e.g. index ltp might be on NSE)
            ltp = self.state.client.get_ltp(f"NSE|{token}") or 25000.0
            
        # 2. Resolve Strike
        expiry_type = params.get('expiry', 'current')
        res = self.state.client.resolver.resolve_option_symbol(symbol, ltp, option_type, strike_logic, expiry_type=expiry_type, exchange=exch)
        
        if not res.get('ok'):
            logging.getLogger("ORBITER").error(f"❌ Resolution Failed: {res.get('reason')}")
            return None
            
        tsym = res['tradingsymbol']
        exch = res['exchange']
        qty = res['lot_size'] * int(params.get('qty_multiplier', 1))
        
        return self._fire(side, tsym, exch, qty, params)

    def _fire(self, side: str, tsym: str, exch: str, qty: int, params: Dict) -> Any:
        logging.getLogger("ORBITER").info(f"⚡ ORDER: {side} {tsym} | QTY: {qty}")
        return self.state.client.api.place_order(
            buy_or_sell=side, 
            product_type=params.get('product', 'MIS'),
            exchange=exch, 
            tradingsymbol=tsym, 
            quantity=qty, 
            discloseqty=0,
            price_type=params.get('price_type', 'MKT'), 
            price=0, 
            retention='DAY', 
            remarks=params.get('remark', 'ORBITER_OPTION')
        )

class OptionSimulationExecutor(OptionActionExecutor):
    """Overrides ONLY the fire mechanism to log instead of trade."""
    def _fire(self, side: str, tsym: str, exch: str, qty: int, params: Dict) -> Any:
        logging.getLogger("ORBITER").info(f"🔬 SIM-OPTION: {side} {tsym} | QTY: {qty}")
        return {"stat": "Ok", "simulated": True, "tsym": tsym}
