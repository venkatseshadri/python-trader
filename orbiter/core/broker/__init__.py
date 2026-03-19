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
    
    def _is_session_expired(self, response) -> bool:
        """Check if response indicates session expired."""
        if isinstance(response, dict):
            stat = response.get('stat', '')
            if stat == 'Not_Ok':
                emsg = response.get('emsg', '')
                if 'session' in emsg.lower() or 'session' in str(emsg).lower():
                    return True
        return False

    def _handle_api_call(self, api_method, *args, max_retries=2, **kwargs):
        """
        Wrapper for API calls that handles session expiry automatically.
        Returns (success, response) tuple.
        """
        for attempt in range(max_retries):
            try:
                response = api_method(*args, **kwargs)
                
                if self._is_session_expired(response):
                    if attempt < max_retries - 1:
                        logger.warning(f"🔑 Session expired. Re-authenticating (attempt {attempt + 1}/{max_retries})...")
                        if self.conn.login():
                            logger.info(f"✅ Re-login successful. Retrying API call...")
                            continue
                    logger.error(f"❌ Session expired and re-authentication failed.")
                    return False, response
                return True, response
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"API call failed: {e}. Retrying...")
                    continue
                logger.error(f"API call failed after {max_retries} attempts: {e}")
                return False, None
        return False, None

    def close(self):
        logger.debug(f"[{self.__class__.__name__}.close] - Closing broker connection.")
        self.conn.close()
    def load_symbol_mapping(self): 
        logger.debug(f"[{self.__class__.__name__}.load_symbol_mapping] - Loading symbol mappings.")
        self.master.load_mappings(self.segment_name)
    def download_scrip_master(self, exchange): 
        logger.debug(f"[{self.__class__.__name__}.download_scrip_master] - Downloading scrip master for exchange: {exchange}.")
        self.master.download_scrip_master(exchange)
    def load_nfo_futures_map(self): 
        logger.debug(f"[{self.__class__.__name__}.load_nfo_futures_map] - Loading NFO futures map.")
        self.master.load_segment_futures_map(self.segment_name)
    
    def get_symbol(self, token, exchange='NSE'): 
        logger.trace(f"[{self.__class__.__name__}.get_symbol] - Getting symbol for token: {token}, exchange: {exchange}")
        return self.master.TOKEN_TO_SYMBOL.get(token, f"{exchange}|{token}")
    def get_company_name(self, token, exchange='NSE'): 
        logger.trace(f"[{self.__class__.__name__}.get_company_name] - Getting company name for token: {token}, exchange: {exchange}")
        return self.master.TOKEN_TO_COMPANY.get(token, self.get_symbol(token, exchange))
    def get_token(self, symbol): 
        logger.trace(f"[{self.__class__.__name__}.get_token] - Getting token for symbol: {symbol}")
        # Handle dict input (e.g., {'symbol': 'ALUMINI', 'token': '487655', ...})
        if isinstance(symbol, dict):
            symbol = symbol.get('symbol') or symbol.get('token') or ''
        if not symbol:
            return None
        result = self.master.SYMBOL_TO_TOKEN.get(symbol.upper(), symbol)
        logger.trace(f"[{self.__class__.__name__}.get_token] - SYMBOL_TO_TOKEN lookup for {symbol.upper()}: {result}")
        return result

