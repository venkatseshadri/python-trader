# orbiter/core/broker/paper_executor.py
"""
Paper Order Executor - Simulated trading with margin checks.
"""

from typing import Dict
from orbiter.core.broker.executor_base import BaseOrderExecutor


class PaperOrderExecutor(BaseOrderExecutor):
    """Paper trading executor with margin checks."""
    
    def __init__(self, api, execution_policy: Dict = None, project_root: str = None, segment_name: str = None):
        super().__init__(api, execution_policy, project_root, segment_name, paper_trade=True)
        
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
    
    def place_option_order(self, option_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        return self._executor.place_option_order(option_details, side, execute, product_type, price_type)
    
    def place_spread(self, spread_details: Dict, execute: bool, product_type: str, price_type: str) -> Dict:
        return self._executor.place_spread(spread_details, execute, product_type, price_type)
