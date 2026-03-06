# orbiter/core/engine/action/executors/equity.py

from .base import BaseActionExecutor
from typing import Dict, Any
from datetime import datetime

class EquityActionExecutor(BaseActionExecutor):
    def execute(self, **params: Dict) -> Any:
        symbol = params.get('symbol')
        exch = params.get('exchange', 'NSE')
        side = params.get('side', 'B').upper()
        qty = int(params.get('qty', 1))
        
        # Check paper trade mode
        paper_trade = self.state.config.get('paper_trade', True)
        if paper_trade:
            return self._simulate(side, symbol, exch, qty, params)
        
        return self._fire(side, symbol, exch, qty, params)

    def _simulate(self, side: str, tsym: str, exch: str, qty: int, params: Dict) -> Any:
        import logging
        logging.getLogger("ORBITER").info(f"🔬 SIM-EQUITY: {side} {tsym} | QTY: {qty}")
        # Add to active_positions for paper trading
        token = params.get('token', tsym)
        token_key = f"{exch}|{token}"
        self.state.active_positions[token_key] = {
            'symbol': tsym,
            'side': side,
            'qty': qty,
            'entry_price': 0,
            'entry_time': datetime.now(),
            'paper': True
        }
        if hasattr(self.state, 'save_paper_positions'):
            self.state.save_paper_positions()
        return {"stat": "Ok", "simulated": True, "tsym": tsym}

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
