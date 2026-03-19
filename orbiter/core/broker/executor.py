# orbiter/core/broker/executor.py
"""
Order Executor Factory for Orbiter.
"""

from typing import Dict
from orbiter.core.engine.action.interfaces import OrderExecutorInterface


def create_executor(api, real_broker_trade: bool, execution_policy: Dict = None, project_root: str = None, segment_name: str = None) -> OrderExecutorInterface:
    """Factory function to create the appropriate executor."""
    if real_broker_trade:
        from orbiter.core.broker.broker_executor import BrokerOrderExecutor
        return BrokerOrderExecutor(api, execution_policy, project_root, segment_name)
    else:
        from orbiter.core.broker.paper_executor import PaperOrderExecutor
        return PaperOrderExecutor(api, execution_policy, project_root, segment_name)
