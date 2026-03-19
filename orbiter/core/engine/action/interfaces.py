# orbiter/core/engine/action/interfaces.py
"""
Order Executor Interface for Orbiter.

This module defines the abstract interface for order execution.
Both PaperOrderExecutor and BrokerOrderExecutor implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class OrderExecutorInterface(ABC):
    """Abstract interface for order execution."""
    
    @abstractmethod
    def place_future_order(self, future_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Place a future order with pre-resolved details."""
        pass
    
    @abstractmethod
    def place_future_order_full(self, symbol: str, exchange: str, side: str, execute: bool, 
                                 product_type: str, price_type: str, token: str = None, **kwargs) -> Dict:
        """Place a future order with full resolution (symbol -> contract details)."""
        pass
    
    @abstractmethod
    def place_option_order(self, option_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Place an option order."""
        pass
    
    @abstractmethod
    def place_spread(self, spread_details: Dict, execute: bool, product_type: str, price_type: str) -> Dict:
        """Place a spread order (multi-leg)."""
        pass
