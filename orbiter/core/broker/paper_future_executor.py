# orbiter/core/broker/paper_future_executor.py
"""
Paper Future Order Executor - simulated future trading with margin checks.
"""

from typing import Dict
from orbiter.core.broker.future_executor import FutureOrderExecutor


class PaperFutureOrderExecutor(FutureOrderExecutor):
    """Paper trading executor for futures with margin checks."""
    
    def __init__(self, api, master, resolver, execution_policy: Dict = None, 
                 project_root: str = None, segment_name: str = None):
        super().__init__(api, master, resolver, execution_policy, project_root, segment_name, paper_trade=True)
        
        from orbiter.utils.margin.margin_executor import MarginAwareExecutor
        self._executor = MarginAwareExecutor(
            api,
            self.logger,
            execution_policy=execution_policy,
            paper_trade=True
        )
        self.logger.info("[PAPER_FUTURE] PaperFutureOrderExecutor initialized")
    
    def _execute_future_order(self, details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Execute future order through margin-aware executor."""
        return self._executor.place_future_order(details, side, execute, product_type, price_type)
    
    def place_option_order(self, option_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Place option order through margin-aware executor."""
        return self._executor.place_option_order(option_details, side, execute, product_type, price_type)
    
    def place_spread(self, spread_details: Dict, execute: bool, product_type: str, price_type: str) -> Dict:
        """Place spread order through margin-aware executor."""
        return self._executor.place_spread(spread_details, execute, product_type, price_type)
