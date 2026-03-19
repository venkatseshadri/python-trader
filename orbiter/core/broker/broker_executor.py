# orbiter/core/broker/broker_executor.py
"""
Broker Order Executor - Real broker trading implementation.
"""

from typing import Dict, List
from orbiter.core.broker.executor_base import BaseOrderExecutor
from orbiter.core.broker.future_executor import FutureOrderExecutor
from orbiter.core.broker.options_executor import OptionsOrderExecutor
from orbiter.core.broker.broker_future_executor import BrokerFutureOrderExecutor
from orbiter.core.broker.broker_options_executor import BrokerOptionsOrderExecutor


class BrokerOrderExecutor(BaseOrderExecutor):
    """Real broker trading executor - composes Future and Options executors."""
    
    def __init__(self, api, master=None, resolver=None, execution_policy: Dict = None, 
                 project_root: str = None, segment_name: str = None):
        super().__init__(api, execution_policy, project_root, segment_name, paper_trade=False)
        self.master = master
        self.resolver = resolver
        self.policy = execution_policy or {}
        
        self._future_executor = BrokerFutureOrderExecutor(
            api, master, resolver, execution_policy, project_root, segment_name
        )
        self._options_executor = BrokerOptionsOrderExecutor(
            api, master, resolver, execution_policy, project_root, segment_name
        )
        
        self.logger.info("[BROKER] BrokerOrderExecutor initialized for live trading")
    
    def place_future_order(self, symbol: str, exchange: str, side: str, execute: bool, 
                          product_type: str, price_type: str, token: str = None, **kwargs) -> Dict:
        """Place a future order with full contract resolution."""
        return self._future_executor.place_future_order(
            symbol, exchange, side, execute, product_type, price_type, token, **kwargs
        )
    
    def place_option_order(self, option_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Place an option order."""
        return self._options_executor.place_option_order(option_details, side, execute, product_type, price_type)
    
    def place_spread(self, spread_details: Dict, execute: bool, product_type: str, price_type: str) -> Dict:
        """Place a spread order."""
        return self._options_executor.place_spread(spread_details, execute, product_type, price_type)
    
    def get_option_theta(self, symbol: str, expiry_date: str, strike_price: float, option_type: str):
        """Get option theta."""
        return self._options_executor.get_option_theta(symbol, expiry_date, strike_price, option_type)
    
    def get_order_history(self) -> List[Dict]:
        """Get order history from order manager."""
        return self.order_manager.get_order_history()
    
    def get_positions(self) -> List[Dict]:
        """Get positions from order manager."""
        return self.order_manager.get_positions()
    
    def record_order(self, order_result: Dict):
        """Record an order in the order manager."""
        self.order_manager.record_order(order_result)
