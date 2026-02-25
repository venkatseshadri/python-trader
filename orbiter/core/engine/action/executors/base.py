# orbiter/core/engine/action/executors/base.py

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager

logger = logging.getLogger("ORBITER")

class BaseActionExecutor(ABC):
    def __init__(self, state):
        self.state = state
        self.constants = ConstantsManager.get_instance()
        self.schema_manager = SchemaManager.get_instance(self.state.client.project_root)

    @abstractmethod
    def execute(self, **params: Dict) -> Any:
        """Entry point for the action. Orchestrates resolution and firing."""
        pass

    @abstractmethod
    def _fire(self, side: str, tsym: str, exch: str, qty: int, params: Dict) -> Any:
        """The actual API call or local log. Overridden by Simulation children."""
        pass
