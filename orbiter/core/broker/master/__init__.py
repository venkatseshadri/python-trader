# orbiter/core/broker/master/__init__.py

import os
import json
import logging # Import logging
import traceback # Import traceback
import datetime
from typing import Dict, Any, Optional, List
from .equity import EquityManager
from .futures import FuturesManager
from .options import OptionsManager
from orbiter.utils.data_manager import DataManager
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.meta_config_manager import MetaConfigManager

logger = logging.getLogger("ORBITER")

class ScripMaster:
    """
    Manages all equity, futures, and options scrip data.
    Loads data from pre-parsed JSON files for quick lookup.
    """
    def __init__(self, project_root: str):
        logger.debug(f"[{self.__class__.__name__}.__init__] - Initializing ScripMaster with project_root: {project_root}")
        self.project_root = project_root
        self.constants = ConstantsManager.get_instance()
        self.meta_config = MetaConfigManager.get_instance(project_root)
        self.project_manifest_schema = self.meta_config.get_key('project_manifest_schema')

        self.TOKEN_TO_SYMBOL: Dict[str, str] = {}
        self.SYMBOL_TO_TOKEN: Dict[str, str] = {}
        self.TOKEN_TO_COMPANY: Dict[str, str] = {}
        self.TOKEN_TO_LOTSIZE: Dict[str, int] = {}
        self.DERIVATIVE_OPTIONS: List[Dict[str, Any]] = [] # Raw list for filters
        self.DERIVATIVE_LOADED = False

        self.equity_manager = EquityManager(project_root)
        self.futures_manager = FuturesManager(project_root)
        self.options_manager = OptionsManager(project_root)
        logger.debug(f"[{self.__class__.__name__}.__init__] - Equity, Futures, Options Managers initialized.")


    def load_mappings(self, segment_name: str):
        """Loads mappings for a specific segment (NFO or MCX)."""
        logger.debug(f"[{self.__class__.__name__}.load_mappings] - Loading mappings for segment: {segment_name}")
        
        # Build data path directly instead of relying on manifest
        data_path = os.path.join(self.project_root, 'orbiter', 'data')

        derivatives_file = None
        if segment_name == 'nfo':
            derivatives_file = os.path.join(data_path, self.constants.get('magic_strings', 'nfo_derivatives_file'))
        elif segment_name == 'bfo':
            # BSE F&O - load from bfo_symbols if available
            bfo_file = os.path.join(data_path, 'bfo_symbols.json')
            if os.path.exists(bfo_file):
                derivatives_file = bfo_file
            else:
                logger.warning(f"BFO symbols file not found at {bfo_file}. Will attempt download.")
                derivatives_file = None
        elif segment_name == 'mcx':
             # 🚀 Fix for MCX segment specific mapping file
            map_file = os.path.join(self.project_root, 'orbiter/data/mcx_futures_map.json')
            if os.path.exists(map_file):
                try:
                    with open(map_file, 'r') as f:
                        mcx_map = json.load(f)
                        for key, info in mcx_map.items():
                            # New format: key is symbol name, info has [symbol, tsym, lot, expiry, token]
                            if isinstance(info, list) and len(info) >= 5:
                                # info[0] = symbol name, info[1] = trading symbol, info[4] = numeric token
                                symbol = str(info[0])
                                trading_symbol = str(info[1])
                                numeric_token = str(info[4])
                                contract = {
                                    'symbol': symbol,
                                    'tradingsymbol': trading_symbol,
                                    'token': numeric_token,  # Use numeric token!
                                    'exchange': 'MCX',
                                    'lotsize': int(info[2]) if len(info) > 2 else 1,
                                    'instrument': 'FUTCOM',
                                    'expiry': info[3] if len(info) > 3 else trading_symbol.replace(symbol, '')
                                }
                                # Use a safer check for duplicates
                                exists = False
                                for d in self.DERIVATIVE_OPTIONS:
                                    if isinstance(d, dict) and d.get('token') == numeric_token:
                                        exists = True
                                        break
                                
                                if not exists:
                                    self.DERIVATIVE_OPTIONS.append(contract)
                                    self.TOKEN_TO_SYMBOL[numeric_token] = trading_symbol
                                    self.SYMBOL_TO_TOKEN[trading_symbol] = numeric_token
                                    self.TOKEN_TO_LOTSIZE[numeric_token] = contract['lotsize']
                                    logger.trace(f"Mapped MCX Future: {numeric_token} -> {trading_symbol} (Lot: {contract['lotsize']})")
                        self.DERIVATIVE_LOADED = True
                        logger.info(f"Loaded {len(mcx_map)} MCX future mappings.")
                        return # Exit after loading MCX
                except Exception as e:
                    logger.error(f"Error loading MCX map: {e}")
                    return
        else:
            logger.warning(f"[{self.__class__.__name__}.load_mappings] - Unknown segment '{segment_name}'. Skipping mapping load.")
            return

        if derivatives_file and os.path.exists(derivatives_file):
            try:
                with open(derivatives_file, 'r') as f:
                    data = json.load(f)
                    options_key = self.constants.get('magic_strings', 'derivatives_options_key', 'options')
                    token_key = self.constants.get('magic_strings', 'derivatives_token_key', 'token')
                    tradingsymbol_key = self.constants.get('magic_strings', 'derivatives_tradingsymbol_key', 'tradingsymbol')
                    companyname_key = self.constants.get('magic_strings', 'derivatives_companyname_key', 'companyname')
                    lotsize_key = self.constants.get('magic_strings', 'derivatives_lotsize_key', 'lotsize')

                    if isinstance(data, list):
                        self.DERIVATIVE_OPTIONS = data
                    else:
                        self.DERIVATIVE_OPTIONS = data.get(options_key, []) if options_key else data
                        # Fallback: if options_key is empty but data is dict, maybe it's the dict itself?
                        if not self.DERIVATIVE_OPTIONS and isinstance(data, dict):
                             self.DERIVATIVE_OPTIONS = list(data.values()) # Risky fallback

                    for item in self.DERIVATIVE_OPTIONS:
                        token = str(item[token_key])
                        self.TOKEN_TO_SYMBOL[token] = item[tradingsymbol_key]
                        self.SYMBOL_TO_TOKEN[item[tradingsymbol_key]] = token
                        self.TOKEN_TO_COMPANY[token] = item[companyname_key]
                        self.TOKEN_TO_LOTSIZE[token] = int(item[lotsize_key])
                    self.DERIVATIVE_LOADED = True
                    logger.info(self.constants.get('magic_strings', 'derivs_loaded_msg').format(count=len(self.DERIVATIVE_OPTIONS), segment=segment_name.upper()))
                    logger.debug(f"[{self.__class__.__name__}.load_mappings] - First 5 loaded derivatives: {self.DERIVATIVE_OPTIONS[:5]}")
            except Exception as e:
                logger.error(f"[{self.__class__.__name__}.load_mappings] - Error loading derivatives from {derivatives_file}: {e}. Traceback: {traceback.format_exc()}")
        
    def download_scrip_master(self, exchange: str):
        """Load the scrip master mappings for the given exchange."""
        logger.debug(f"[{self.__class__.__name__}.download_scrip_master] - Loading mappings for exchange: {exchange}.")
        
        # Map exchange to segment name
        segment_map = {'MCX': 'mcx', 'NFO': 'nfo', 'BFO': 'bfo', 'NSE': 'nse'}
        segment = segment_map.get(exchange.upper(), exchange.lower())
        
        # Load mappings for the segment
        self.load_mappings(segment)
    
    def _parse_expiry_date(self, raw: str) -> Optional["datetime.date"]:
        if not raw: return None
        for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d", "%d%b%y", "%d%b%Y"):
            try: return datetime.datetime.strptime(raw.upper(), fmt).date()
            except ValueError: continue
        return None

    def check_and_update_mcx_expiry(self) -> bool:
        """Check if any MCX contracts are expired and update if needed. Returns True if update was performed."""
        if not self.DERIVATIVE_OPTIONS:
            return False
        
        today = datetime.datetime.now().date()
        expired_contracts = []
        
        for contract in self.DERIVATIVE_OPTIONS:
            if contract.get('exchange') != 'MCX':
                continue
            expiry_str = contract.get('expiry', '')
            if not expiry_str:
                continue
            expiry_date = self._parse_expiry_date(expiry_str)
            if expiry_date and expiry_date < today:
                expired_contracts.append(contract)
        
        if expired_contracts:
            logger.warning(f"Found {len(expired_contracts)} expired MCX contracts: {[c.get('tradingsymbol') for c in expired_contracts]}")
            logger.info("Calling update_mcx_config.py to refresh contracts...")
            try:
                from orbiter.utils.mcx import update_mcx_config
                update_mcx_config.main()
                self.load_mappings('mcx')
                logger.info("MCX contracts updated successfully.")
                return True
            except Exception as e:
                logger.error(f"Failed to update MCX contracts: {e}")
                return False
        
        return False

    def get_equity_token(self, symbol: str) -> Optional[str]:
        logger.trace(f"[{self.__class__.__name__}.get_equity_token] - Getting equity token for symbol: {symbol}")
        return self.equity_manager.get_token(symbol)

    def get_futures_token(self, symbol: str) -> Optional[str]:
        logger.trace(f"[{self.__class__.__name__}.get_futures_token] - Getting futures token for symbol: {symbol}")
        return self.futures_manager.get_token(symbol)

    def get_options_token(self, symbol: str) -> Optional[str]:
        logger.trace(f"[{self.__class__.__name__}.get_options_token] - Getting options token for symbol: {symbol}")
        return self.options_manager.get_token(symbol)
