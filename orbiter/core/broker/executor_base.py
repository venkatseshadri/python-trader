# orbiter/core/broker/executor_base.py
"""
Base classes for Order Executors.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Dict
from orbiter.core.engine.action.interfaces import OrderExecutorInterface


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
    
    def __init__(self, api, execution_policy: Dict = None, project_root: str = None, segment_name: str = None):
        self.api = api
        self.execution_policy = execution_policy or {}
        self.logger = _create_logger(project_root, segment_name)
