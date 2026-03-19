# orbiter/core/broker/paper_executor.py
"""
Paper Order Executor - Simulated trading with margin checks.
"""

import logging
import os
from typing import Dict, List
from orbiter.core.broker.future_executor import FutureOrderExecutor
from orbiter.core.broker.options_executor import OptionsOrderExecutor
from orbiter.core.broker.paper_future_executor import PaperFutureOrderExecutor
from orbiter.core.broker.paper_options_executor import PaperOptionsOrderExecutor


def _create_logger(project_root: str, segment_name: str) -> logging.Logger:
    """Create a logger for trade calls."""
    log_dir = os.path.join(project_root, 'logs', segment_name)
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, 'trade_calls.log')
    
    logger = logging.getLogger(f"trade_calls_{segment_name}")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        h = logging.FileHandler(path)
        h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(h)
    return logger


class PaperOrderExecutor:
    """Paper trading executor with margin checks - composes Future and Options executors."""
    
    def __init__(self, api, master=None, resolver=None, execution_policy: Dict = None, 
                 project_root: str = None, segment_name: str = None):
        self.api = api
        self.master = master
        self.resolver = resolver
        self.policy = execution_policy or {}
        self.project_root = project_root
        self.segment_name = segment_name
        
        self.logger = _create_logger(project_root, segment_name)
        
        self._future_executor = PaperFutureOrderExecutor(
            api, master, resolver, execution_policy, project_root, segment_name
        )
        self._options_executor = PaperOptionsOrderExecutor(
            api, master, resolver, execution_policy, project_root, segment_name
        )
        
        self.logger.info("[PAPER] PaperOrderExecutor initialized with margin checks")
    
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
        """Get order history from future and options executors."""
        future_orders = self._future_executor.get_order_history()
        option_orders = self._options_executor.get_order_history()
        return future_orders + option_orders
    
    def get_positions(self) -> List[Dict]:
        """Get positions from future and options executors."""
        future_positions = self._future_executor.get_positions()
        option_positions = self._options_executor.get_positions()
        return future_positions + option_positions
    
    def record_order(self, order_result: Dict):
        """Record an order in the appropriate executor."""
        if 'future' in str(order_result.get('tsym', '')).lower():
            self._future_executor.record_order(order_result)
        else:
            self._options_executor.record_order(order_result)
