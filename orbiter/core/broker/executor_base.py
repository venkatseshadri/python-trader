# orbiter/core/broker/executor_base.py
"""
Base classes for Order Executors.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, List
from orbiter.core.engine.action.interfaces import OrderExecutorInterface
from orbiter.core.broker.order_manager import OrderManager


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


class BaseOrderExecutor(ABC):
    """Base class with common implementation for order executors."""
    
    def __init__(self, api, execution_policy: Dict = None, project_root: str = None, segment_name: str = None, paper_trade: bool = False):
        self.api = api
        self.execution_policy = execution_policy or {}
        self.project_root = project_root
        self.segment_name = segment_name
        self.paper_trade = paper_trade
        self.logger = _create_logger(project_root, segment_name)
        self.order_manager = OrderManager(project_root, segment_name, paper_trade)
    
    def record_order(self, order_result: Dict):
        """Record an order in the order manager."""
        self.order_manager.record_order(order_result)
    
    def get_order_history(self) -> List[Dict]:
        """Get order history from order manager."""
        return self.order_manager.get_order_history()
    
    def get_positions(self) -> List[Dict]:
        """Get positions from order manager."""
        return self.order_manager.get_positions()
