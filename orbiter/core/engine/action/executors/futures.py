# orbiter/core/engine/action/executors/futures.py

from .base import BaseActionExecutor
from typing import Dict, Any
import logging

def _get_exchange_value(client, exch: str, key: str, default=None):
    """Helper to get value from exchange config with fallback to defaults."""
    exch_config = getattr(client, 'exchange_config', {})
    # Try exchange-specific config
    segment_config = exch_config.get(exch.lower(), {})
    value = segment_config.get('plumbing', {}).get(key) or segment_config.get('execution_policy', {}).get(key)
    if value:
        return value
    # Fall back to global defaults
    defaults = exch_config.get('defaults', {})
    return defaults.get(key, default)

class FutureActionExecutor(BaseActionExecutor):
    def execute(self, **params: Dict) -> Any:
        symbol = params.get('symbol')
        side = params.get('side', 'B').upper()
        
        # Check if paper trading is enabled
        paper_trade = self.state.config.get('paper_trade', True)
        execute = not paper_trade  # execute=True means LIVE
        
        # Determine exchange - use param or derive from broker segment
        exchange = params.get('exchange')
        if not exchange:
            exchange = _get_exchange_value(self.state.client, 'nfo', 'segment_name', 'NFO')
        
        # Get defaults from exchange config
        product_type = params.get('product') or _get_exchange_value(self.state.client, exchange, 'default_product', 'I')
        price_type = params.get('price_type') or _get_exchange_value(self.state.client, exchange, 'default_price_type', 'LMT')
        
        # Resolve Future Contract
        res = self.state.client.place_future_order(
            symbol=symbol,
            exchange=exchange,
            side=side,
            execute=execute,
            product_type=product_type,
            price_type=price_type
        )
        
        # Handle both 'tsym' and 'tradingsymbol' response keys
        tsym = res.get('tsym') or res.get('tradingsymbol')
        if not tsym:
            logging.getLogger("ORBITER").error(f"❌ Future Resolution Failed for {symbol}")
            return None
            
        exch = res.get('exchange', exchange)
        qty = res.get('lot_size', 1)
        
        # If simulation mode, return simulated response
        if not execute:
            return {"stat": "Ok", "simulated": True, "tsym": tsym, "side": side, "qty": qty}
        
        return self._fire(side, tsym, exch, qty, params, product_type, price_type)

    def _fire(self, side: str, tsym: str, exch: str, qty: int, params: Dict, product_type: str, price_type: str) -> Any:
        # Get retention from config
        retention = _get_exchange_value(self.state.client, exch, 'retention', 'DAY')
        remarks_template = _get_exchange_value(self.state.client, exch, 'remarks_template', 'ORBITER_FUTURE')
        remarks = params.get('remark', remarks_template)
        
        logging.getLogger("ORBITER").info(f"⚡ ORDER: {side} {tsym} | QTY: {qty}")
        return self.state.client.api.place_order(
            buy_or_sell=side, 
            product_type=product_type,
            exchange=exch, 
            tradingsymbol=tsym, 
            quantity=qty, 
            discloseqty=0,
            price_type=price_type, 
            price=0, 
            retention=retention, 
            remarks=remarks
        )

class FutureSimulationExecutor(FutureActionExecutor):
    def execute(self, **params: Dict) -> Any:
        # Override to force simulation mode
        params['execute'] = False
        return super().execute(**params)
