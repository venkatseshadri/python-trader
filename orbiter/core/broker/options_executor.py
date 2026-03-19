# orbiter/core/broker/options_executor.py
"""
Options Order Executor - base class for option order placement and Greeks.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
from orbiter.core.broker.executor_base import BaseOrderExecutor


class OptionsOrderExecutor(BaseOrderExecutor):
    """Base executor for option orders with Greeks calculation and order management."""
    
    def __init__(self, api, master=None, resolver=None, execution_policy: Dict = None, 
                 project_root: str = None, segment_name: str = None, paper_trade: bool = False):
        super().__init__(api, execution_policy, project_root, segment_name, paper_trade)
        self.master = master
        self.resolver = resolver
        self.policy = self.execution_policy or {}
    
    def get_option_theta(self, symbol: str, expiry_date: str, strike_price: float, option_type: str) -> Optional[float]:
        """Fetches the Theta value for a given option contract."""
        self.logger.debug(f"[{self.__class__.__name__}.get_option_theta] - Fetching Theta for {symbol}, Expiry: {expiry_date}, Strike: {strike_price}, Type: {option_type}")
        
        if not self.master:
            self.logger.error(f"[{self.__class__.__name__}.get_option_theta] - Master not available")
            return None
        
        try:
            token = self.master.SYMBOL_TO_TOKEN.get(symbol.upper())
            if not token:
                self.logger.error(f"[{self.__class__.__name__}.get_option_theta] - Could not find token for symbol: {symbol}")
                return None
            
            spot_key = f"{self.segment_name.upper() if self.segment_name else 'NSE'}|{token}"
            spot_price = 0.0
            if hasattr(self, 'SYMBOLDICT'):
                live_data = self.SYMBOLDICT.get(spot_key)
                if live_data:
                    spot_price = float(live_data.get('ltp') or live_data.get('lp') or 0.0)
            
            if spot_price == 0.0:
                self.logger.warning(f"[{self.__class__.__name__}.get_option_theta] - Spot price not available for {symbol}")
            
            ret = self.api.option_greek(
                expiredate=expiry_date,
                StrikePrice=str(strike_price),
                SpotPrice=str(spot_price),
                InterestRate='10',
                Volatility='20',
                OptionType=option_type.upper()
            )
            
            if ret and ret.get('stat') == 'Ok':
                theta = float(ret.get('theta', 0.0))
                self.logger.debug(f"[{self.__class__.__name__}.get_option_theta] - Fetched Theta: {theta}")
                return theta
            else:
                self.logger.warning(f"[{self.__class__.__name__}.get_option_theta] - API call returned non-OK status: {ret}")
                return None
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}.get_option_theta] - Error fetching option greek: {e}")
            return None
    
    @abstractmethod
    def place_option_order(self, option_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Execute the actual option order - implement in subclasses."""
        pass
