# orbiter/core/engine/action/executors/equity.py

from .base import BaseActionExecutor
from typing import Dict, Any

class EquityActionExecutor(BaseActionExecutor):
    def execute(self, **params: Dict) -> Any:
        symbol = params.get('symbol')
        exch = params.get('exchange', 'NSE')
        side = params.get('side', 'B').upper()
        qty = int(params.get('qty', 1))
        
        return self._fire(side, symbol, exch, qty, params)

    def _fire(self, side: str, tsym: str, exch: str, qty: int, params: Dict) -> Any:
        self._log_fire(side, tsym, qty, live=True)
        return self.state.client.api.place_order(
            buy_or_sell=side, 
            product_type=params.get('product', 'MIS'),
            exchange=exch, 
            tradingsymbol=tsym, 
            quantity=qty, 
            discloseqty=0,
            price_type=params.get('price_type', 'MKT'), 
            price=params.get('price', 0), 
            retention='DAY', 
            remarks=params.get('remark', 'ORBITER_EQUITY')
        )

    def _log_fire(self, side, tsym, qty, live=True):
        prefix = "⚡ ORDER" if live else "🔬 SIM-ORDER"
        import logging
        logging.getLogger("ORBITER").info(f"{prefix}: {side} {tsym} | QTY: {qty}")

class EquitySimulationExecutor(EquityActionExecutor):
    """Generic Simulation Executor for Equities or simple instruments."""
    def _fire(self, side: str, tsym: str, exch: str, qty: int, params: Dict) -> Any:
        self._log_fire(side, tsym, qty, live=False)
        return {"stat": "Ok", "simulated": True, "tsym": tsym}
