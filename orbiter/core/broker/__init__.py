"""
BrokerClient - Central Gateway for Broker API Interactions.

This module provides the BrokerClient class which acts as a unified interface
to the broker's trading API. It composes several specialized managers:

- conn: ConnectionManager - WebSocket connection and session management
- master: ScripMaster - Market data and instrument definitions
- resolver: ContractResolver - Contract resolution for orders
- margin: MarginCalculator - Margin calculations
- executor: OrderExecutor - Order placement (paper or live)
- conn.tick_handler: TickHandler - Real-time tick data management

Usage:
    from orbiter.core.broker import BrokerClient
    
    client = BrokerClient(project_root="/path/to/project", segment_name="nse")
    client.executor.place_future_order(...)
    
    # Access tick data
    client.conn.tick_handler.SYMBOLDICT
    
    # Access master data
    client.master.TOKEN_TO_SYMBOL
"""

import logging
from typing import Dict
from .connection import ConnectionManager
from .master import ScripMaster
from .resolver import ContractResolver
from orbiter.utils.margin.margin_calculator import MarginCalculator
from orbiter.utils.constants_manager import ConstantsManager

logger = logging.getLogger("ORBITER")


class BrokerClient:
    """
    Central Gateway for Broker API Interactions.
    
    Provides a unified interface to the broker's trading API by composing
    specialized managers for different functionalities.
    """
    
    _MASTERS: Dict[str, ScripMaster] = {}  # Cached masters per segment

    def __init__(
        self,
        project_root: str,
        segment_name: str,
        real_broker_trade: bool = False
    ):
        """
        Initialize BrokerClient.
        
        Args:
            project_root: Path to project root directory
            segment_name: Exchange segment (e.g., 'nse', 'nfo', 'mcx')
            real_broker_trade: If True, place real orders; if False, paper trade
        """
        if not project_root:
            raise ValueError("project_root is required")
        if not segment_name:
            raise ValueError("segment_name is required")
        
        self.real_broker_trade = real_broker_trade
        self.project_root = project_root
        self.segment_name = segment_name.lower()
        self.constants = ConstantsManager.get_instance()
        
        # Connection management (WebSocket, session, auth)
        self.conn = ConnectionManager()
        
        # Market data master (cached per segment)
        if self.segment_name not in BrokerClient._MASTERS:
            BrokerClient._MASTERS[self.segment_name] = ScripMaster(project_root)
        self.master = BrokerClient._MASTERS[self.segment_name]
        
        # Contract resolution for orders
        self.resolver = ContractResolver(self.master, api=self.conn.api)
        
        # Margin calculations
        config = self._load_config('broker_config')
        cache_path = config.get('span_cache_path') if config else None
        self.margin = MarginCalculator(self.master, cache_path)
        
        # Tick data management
        from orbiter.core.broker.tick_handler import TickHandler
        self.conn.tick_handler = TickHandler(
            self.conn.api, self.master, project_root, self.segment_name
        )
        
        # Execution policy
        exch_config = self._load_config('exchange_config')
        policy = exch_config.get(self.segment_name, {}).get('execution_policy', {})
        
        # Order executor (paper or live)
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
        
        logger.info(f"[BrokerClient] Initialized for {segment_name} (real_trade={real_broker_trade})")

    def _load_config(self, config_name: str) -> Dict:
        """Load configuration file."""
        from orbiter.utils.data_manager import DataManager
        return DataManager.load_config(self.project_root, 'optional_files', config_name) or {}
