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
        self.constants = ConstantsManager.get_instance(project_root)
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
        data_structure_key = self.project_manifest_schema.get('structure_key', 'structure')
        data_path = DataManager.get_manifest_path(self.project_root, data_structure_key, 'data')

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
                        for tok, info in mcx_map.items():
                            if isinstance(info, list) and len(info) >= 2:
                                # Create a mock derivative option dictionary
                                trading_symbol = str(info[1])
                                contract = {
                                    'symbol': str(info[0]),
                                    'tradingsymbol': trading_symbol,
                                    'token': str(tok),
                                    'exchange': 'MCX',
                                    'lotsize': int(info[2]) if len(info) > 2 else 1,
                                    'instrument': 'FUTCOM',
                                    'expiry': trading_symbol.replace(str(info[0]), '') # Approximation
                                }
                                # Refine expiry string for format_date (e.g. 19MAR26)
                                if contract['expiry'].startswith('M') and len(contract['expiry']) > 1:
                                    # Handle mini prefix 'M'
                                    possible_date = contract['expiry'][1:]
                                    if possible_date:
                                        contract['expiry'] = possible_date

                                # Use a safer check for duplicates
                                exists = False
                                for d in self.DERIVATIVE_OPTIONS:
                                    if isinstance(d, dict) and d.get('token') == str(tok):
                                        exists = True
                                        break
                                
                                if not exists:
                                    self.DERIVATIVE_OPTIONS.append(contract)
                                    self.TOKEN_TO_SYMBOL[str(tok)] = contract['tradingsymbol']
                                    self.SYMBOL_TO_TOKEN[contract['tradingsymbol']] = str(tok)
                                    self.TOKEN_TO_LOTSIZE[str(tok)] = contract['lotsize']
                                    logger.trace(f"Mapped MCX Future: {tok} -> {contract['tradingsymbol']} (Lot: {contract['lotsize']})")
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
        for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try: return datetime.datetime.strptime(raw, fmt).date()
            except ValueError: continue
        return None

    def get_equity_token(self, symbol: str) -> Optional[str]:
        logger.trace(f"[{self.__class__.__name__}.get_equity_token] - Getting equity token for symbol: {symbol}")
        return self.equity_manager.get_token(symbol)

    def get_futures_token(self, symbol: str) -> Optional[str]:
        logger.trace(f"[{self.__class__.__name__}.get_futures_token] - Getting futures token for symbol: {symbol}")
        return self.futures_manager.get_token(symbol)

    def get_options_token(self, symbol: str) -> Optional[str]:
        logger.trace(f"[{self.__class__.__name__}.get_options_token] - Getting options token for symbol: {symbol}")
        return self.options_manager.get_token(symbol)
