# orbiter/core/engine/action/executors/futures.py

from .base import BaseActionExecutor
from typing import Dict, Any
import logging

class FutureActionExecutor(BaseActionExecutor):
    def execute(self, **params: Dict) -> Any:
        symbol = params.get('symbol')
        side = params.get('side', 'B').upper()
        
        # 1. Resolve Future Contract (Near/Far etc - wrapper for broker client)
        res = self.state.client.place_future_order(
            symbol=symbol,
            side=side,
            execute=False, # Use our own _fire mechanism
            product_type=params.get('product', 'MIS'),
            price_type=params.get('price_type', 'MKT')
        )
        
        if not res.get('tsym'):
            logging.getLogger("ORBITER").error(f"❌ Future Resolution Failed for {symbol}")
            return None
            
        tsym = res['tsym']
        exch = res.get('exchange', 'NFO')
        qty = res.get('lot_size', 1)
        
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
            remarks=params.get('remark', 'ORBITER_FUTURE')
        )

class FutureSimulationExecutor(FutureActionExecutor):
    def _fire(self, side: str, tsym: str, exch: str, qty: int, params: Dict) -> Any:
        logging.getLogger("ORBITER").info(f"🔬 SIM-FUTURE: {side} {tsym} | QTY: {qty}")
        return {"stat": "Ok", "simulated": True, "tsym": tsym}
