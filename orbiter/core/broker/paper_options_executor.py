# orbiter/core/broker/paper_options_executor.py
"""
Paper Options Order Executor - simulated option trading with margin checks.
"""

from typing import Dict
from orbiter.core.broker.options_executor import OptionsOrderExecutor


class PaperOptionsOrderExecutor(OptionsOrderExecutor):
    """Paper trading executor for options with margin checks."""
    
    def __init__(self, api, master=None, resolver=None, execution_policy: Dict = None, 
                 project_root: str = None, segment_name: str = None):
        super().__init__(api, master, resolver, execution_policy, project_root, segment_name, paper_trade=True)
        
        from orbiter.utils.margin.margin_executor import MarginAwareExecutor
        self._executor = MarginAwareExecutor(
            api,
            self.logger,
            execution_policy=execution_policy,
            paper_trade=True
        )
        self.logger.info("[PAPER_OPTIONS] PaperOptionsOrderExecutor initialized")
    
    def _execute_option_order(self, option_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Execute option order through margin-aware executor."""
        return self._executor.place_option_order(option_details, side, execute, product_type, price_type)
    
    def place_option_order(self, option_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Place option order - delegates to _execute_option_order."""
        return self._execute_option_order(option_details, side, execute, product_type, price_type)
    
    def place_spread(self, spread_details: Dict, execute: bool, product_type: str, price_type: str) -> Dict:
        """Place spread order through margin-aware executor."""
        return self._executor.place_spread(spread_details, execute, product_type, price_type)
