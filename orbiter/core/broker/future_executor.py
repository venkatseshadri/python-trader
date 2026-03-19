# orbiter/core/broker/future_executor.py
"""
Future Order Executor - base class for future order placement.
"""

from abc import ABC, abstractmethod
from typing import Dict
from orbiter.core.broker.executor_base import BaseOrderExecutor


class FutureOrderExecutor(BaseOrderExecutor):
    """Base executor for future orders with contract resolution."""
    
    def __init__(self, api, master=None, resolver=None, execution_policy: Dict = None, 
                 project_root: str = None, segment_name: str = None, paper_trade: bool = False):
        super().__init__(api, execution_policy, project_root, segment_name, paper_trade)
        self.master = master
        self.resolver = resolver
        self.policy = self.execution_policy or {}
    
    def place_future_order(self, symbol: str, exchange: str, side: str, execute: bool, 
                          product_type: str, price_type: str, token: str = None, **kwargs) -> Dict:
        """Place a future order with full contract resolution."""
        exchange = exchange or 'NFO'
        
        if not self.resolver:
            return {'ok': False, 'reason': 'resolver_not_available'}
        
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
        
        result = self._execute_future_order(details, side, execute, product_type, price_type)
        if result.get('ok'):
            self.record_order(result)
        return result
    
    @abstractmethod
    def _execute_future_order(self, details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Execute the actual future order - implement in subclasses."""
        pass
