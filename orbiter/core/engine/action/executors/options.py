# orbiter/core/engine/action/executors/options.py

from .base import BaseActionExecutor
from typing import Dict, Any
from datetime import datetime
import logging

class OptionActionExecutor(BaseActionExecutor):
    def execute(self, **params: Dict) -> Any:
        symbol = params.get('symbol', 'NIFTY')
        # Support both 'option' and 'option_type' keys from rules.json
        option_type = params.get('option') or params.get('option_type') # CE or PE
        # Support both 'strike' and 'strike_logic' keys from rules.json
        strike_logic = params.get('strike') or params.get('strike_logic') # ATM, ATM+2, etc
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
        # Support both 'expiry' and 'expiry_type' keys from rules.json
        expiry_type = params.get('expiry') or params.get('expiry_type') or 'current'
        res = self.state.client.resolver.resolve_option_symbol(symbol, ltp, option_type, strike_logic, expiry_type=expiry_type, exchange=exch)
        
        if not res.get('ok'):
            logging.getLogger("ORBITER").error(f"❌ Resolution Failed: {res.get('reason')}")
            return None
            
        tsym = res['tradingsymbol']
        exch = res['exchange']
        qty = res['lot_size'] * int(params.get('qty_multiplier', 1))
        
        # Check paper trade mode
        paper_trade = self.state.config.get('paper_trade', True)
        if paper_trade:
            logging.getLogger("ORBITER").info(f"🔬 SIM-OPTION: {side} {tsym} | QTY: {qty}")
            # Add to active_positions for paper trading
            token_key = f"{exch}|{token}"
            self.state.active_positions[token_key] = {
                'symbol': tsym,
                'side': side,
                'qty': qty,
                'entry_price': ltp,
                'entry_time': datetime.now(),
                'paper': True
            }
            # Save paper positions to disk
            if hasattr(self.state, 'save_paper_positions'):
                self.state.save_paper_positions()
            return {"stat": "Ok", "simulated": True, "tsym": tsym}
        
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
