import os
import logging
import json
import traceback
from typing import Dict, Optional, Any, List
from .connection import ConnectionManager
from .master import ScripMaster
from .resolver import ContractResolver
from orbiter.utils.margin.margin_calculator import MarginCalculator
from orbiter.utils.constants_manager import ConstantsManager

logger = logging.getLogger("ORBITER")

class BrokerClient:
    """
    🚀 Central Gateway for Shoonya API Interactions.
    """
    _MASTERS: Dict[str, ScripMaster] = {}  # Segment-aware Masters

    def __init__(
        self,
        project_root: str,
        segment_name: str,
        real_broker_trade: bool = False
    ):
        if not project_root:
            raise ValueError("project_root is required. Cannot be None or empty.")
        if not segment_name:
            raise ValueError("segment_name is required. Cannot be None or empty.")
        
        # real_broker_trade=false means paper trading (default safe)
        self.real_broker_trade = real_broker_trade
        
        logger.debug(
            f"[{self.__class__.__name__}.__init__] - "
            f"Initializing BrokerClient for segment: {segment_name}"
        )
        self.project_root = project_root
        self.segment_name = segment_name.lower()
        self.constants = ConstantsManager.get_instance()
        self.conn = ConnectionManager()

        if self.segment_name not in BrokerClient._MASTERS:
            BrokerClient._MASTERS[self.segment_name] = ScripMaster(project_root)
            logger.debug(
                f"[{self.__class__.__name__}.__init__] - "
                f"Initialized ScripMaster for segment: {self.segment_name.upper()}"
            )

        self.master = BrokerClient._MASTERS[self.segment_name]
        self.resolver = ContractResolver(self.master, api=self.conn.api)
        
        from orbiter.utils.data_manager import DataManager
        config = DataManager.load_config(project_root, 'optional_files', 'broker_config')
        cache_path = config.get('span_cache_path') if config else None
        self.margin = MarginCalculator(self.master, cache_path)
        
        from orbiter.core.broker.tick_handler import TickHandler
        self.conn.tick_handler = TickHandler(self.conn.api, self.master, project_root, self.segment_name)

        # Load Execution Policy for the segment
        from orbiter.utils.data_manager import DataManager
        exch_config = DataManager.load_config(
            project_root, 'mandatory_files', 'exchange_config'
        )
        self.exchange_config = exch_config
        policy = exch_config.get(self.segment_name, {}).get('execution_policy', {})

        # Use factory to create appropriate executor based on real_broker_trade
        from orbiter.core.broker.executor import create_executor
        self.executor = create_executor(
            self.conn.api,
            master=self.master,
            resolver=self.resolver,
            real_broker_trade=self.real_broker_trade,
            execution_policy=policy,
            project_root=project_root,
            segment_name=self.segment_name
        )
        logger.debug(
            f"[{self.__class__.__name__}.__init__] - "
            "Resolver, Margin, Executor (with policy) initialized."
        )
        
        self._local_symbol_dict: Dict[str, Dict[str, Any]] = {}
    
    @property
    def SYMBOLDICT(self) -> Dict[str, Dict[str, Any]]:
        """Get symbol dict from tick handler."""
        return self.conn.tick_handler.SYMBOLDICT


    @property
    def api(self): return self.conn.api
    @property
    def TOKEN_TO_SYMBOL(self): return self.master.TOKEN_TO_SYMBOL
    @property
    def SYMBOL_TO_TOKEN(self): return self.master.SYMBOL_TO_TOKEN
    @property
    def TOKEN_TO_COMPANY(self): return self.master.TOKEN_TO_COMPANY
    @property
    def TOKEN_TO_LOTSIZE(self): return self.master.TOKEN_TO_LOTSIZE
    @property
    def DERIVATIVE_OPTIONS(self): return self.master.DERIVATIVE_OPTIONS
    @property
    def DERIVATIVE_LOADED(self): return self.master.DERIVATIVE_LOADED

