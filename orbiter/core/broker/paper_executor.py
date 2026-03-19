# orbiter/core/broker/paper_executor.py
"""
Paper Order Executor - Simulated trading with margin checks.
"""

from typing import Dict
from orbiter.core.broker.executor_base import BaseOrderExecutor


class PaperOrderExecutor(BaseOrderExecutor):
    """Paper trading executor with margin checks."""
    
    def __init__(self, api, master=None, resolver=None, execution_policy: Dict = None, 
                 project_root: str = None, segment_name: str = None):
        super().__init__(api, execution_policy, project_root, segment_name, paper_trade=True)
        self.master = master
        self.resolver = resolver
        
        from orbiter.utils.margin.margin_executor import MarginAwareExecutor
        self._executor = MarginAwareExecutor(
            api,
            self.logger,
            execution_policy=execution_policy,
            paper_trade=True
        )
        self.logger.info("[PAPER] PaperOrderExecutor initialized with margin checks")
    
    def place_future_order(self, future_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        return self._executor.place_future_order(future_details, side, execute, product_type, price_type)
    
    def place_future_order_full(self, symbol: str, exchange: str, side: str, execute: bool, 
                                product_type: str, price_type: str, token: str = None, **kwargs) -> Dict:
        """Place future order with full resolution (symbol -> contract details)."""
        if not self.resolver:
            return {'ok': False, 'reason': 'resolver_not_available'}
        
        exchange = exchange or 'NFO'
        res = self.resolver.get_near_future(symbol, exchange, self.api)
        
        if not res and token:
            token_in = str(token)
            if self.master:
                tsym = self.master.TOKEN_TO_SYMBOL.get(token_in)
                if tsym:
                    res = {'token': token_in, 'tsym': tsym}
        
        if not res:
            return {'ok': False, 'reason': 'future_not_found'}
        
        lot_size = 0
        if hasattr(self, 'SYMBOLDICT'):
            live_data = self.SYMBOLDICT.get(res['token'])
            if live_data and live_data.get('ls'):
                lot_size = int(live_data['ls'])
        
        if lot_size <= 0 and self.master:
            tsym = res.get('tsym') or res.get('tradingsymbol')
            for r in self.master.DERIVATIVE_OPTIONS:
                if r.get('tradingsymbol') == tsym:
                    lot_size = int(r.get('lotsize', 0))
                    break
        
        if lot_size <= 0:
            return {'ok': False, 'reason': 'invalid_lot_size'}
        
        tsym = res.get('tsym') or res.get('tradingsymbol')
        details = {'tsym': tsym, 'lot_size': lot_size, 'exchange': exchange, 'token': res.get('token', '')}
        
        result = self.place_future_order(details, side, execute, product_type, price_type)
        self.record_order(result)
        return result
    
    def place_option_order(self, option_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        return self._executor.place_option_order(option_details, side, execute, product_type, price_type)
    
    def place_spread(self, spread_details: Dict, execute: bool, product_type: str, price_type: str) -> Dict:
        return self._executor.place_spread(spread_details, execute, product_type, price_type)
