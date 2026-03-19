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

    def prime_candles(self, symbols: List[Any], lookback_mins: int = 300):
        logger.debug(f"[{self.__class__.__name__}.prime_candles] - Priming {len(symbols)} symbols with last {lookback_mins} minutes data.")
        if not symbols: return
        print(self.constants.get('magic_strings', 'prime_candles_start_msg', "⏳ Priming {count} symbols...").format(count=len(symbols), minutes=lookback_mins))
        
        from datetime import datetime, timedelta
        import pytz
        
        ist = pytz.timezone('Asia/Kolkata')
        end_dt = datetime.now(ist)
        start_dt = end_dt - timedelta(minutes=lookback_mins + 15)
        
        success_count = 0
        for item in symbols:
            logger.trace(f"[{self.__class__.__name__}.prime_candles] - Priming item: {item}")
            try:
                token = ''
                exch = 'NSE'  # Default exchange
                
                if isinstance(item, dict):
                    # Use token directly if available, else get it from symbol
                    token = item.get('token', '')
                    # CRITICAL: Ensure token is string for comparison
                    token = str(token) if token else ''
                    # FIX: If token is already numeric, use it directly without resolution
                    if token.isdigit():
                        # Token is already numeric (e.g., '487655'), use it directly
                        exch = item.get('exchange', 'NSE')
                        key = f"{exch}|{token}"
                        ex, tk = key.split('|')
                        # Get interval from strategy parameters, default to 5 minutes
                        interval = self._priming_interval if hasattr(self, '_priming_interval') else 5
                        res = self.api.get_time_price_series(
                            exchange=ex, 
                            token=tk, 
                            starttime=start_dt.timestamp(), 
                            endtime=end_dt.timestamp(), 
                            interval=interval
                        )
                        
                        # Store candles in SYMBOLDICT
                        if res and isinstance(res, list):
                            if key not in self.SYMBOLDICT:
                                sym = self.get_symbol(tk, exchange=ex)
                                self.SYMBOLDICT[key] = {
                                    'symbol': sym, 't': sym, 'company_name': self.get_company_name(tk, exchange=ex),
                                    'token': tk, 'exchange': ex, 'ltp': float(res[-1]['intc']),
                                    'high': float(res[-1].get('inth', 0)), 'low': float(res[-1].get('intl', 0)), 
                                    'volume': int(res[-1].get('v', 0))
                                }
                            self.SYMBOLDICT[key]['candles'] = res
                            success_count += 1
                            logger.debug(f"[{self.__class__.__name__}.prime_candles] - Primed {key} with {len(res)} candles. Last: {res[-1].get('intc', '?')}")
                        else:
                            logger.warning(f"[{self.__class__.__name__}.prime_candles] - No history returned for {key}. Live feed will populate data.")
                        
                        # Add delay to avoid rate limiting
                        import time
                        time.sleep(0.1)
                        continue
                
                # CRITICAL: If token is a symbol name (not numeric), resolve it
                logger.trace(f"[prime_candles] DEBUG: token='{token}', isdigit={token.isdigit() if token else 'empty'}")
                if token and isinstance(token, str) and not token.isdigit():
                    logger.trace(f"[{self.__class__.__name__}.prime_candles] - Token '{token}' is symbol name, resolving to numeric...")
                    
                    # FIX: Check if symbol exists in mcx_futures_map.json
                    # Use direct lookup first (avoids prefix matching bugs)
                    import json
                    import os
                    numeric_token = None
                    futures_map_path = os.path.join(self.project_root, 'orbiter', 'data', 'mcx_futures_map.json')
                    
                    if os.path.exists(futures_map_path):
                        try:
                            with open(futures_map_path, 'r') as f:
                                mcx_map = json.load(f)
                            # Check if symbol exists in futures_map (key is symbol name like 'ZINC')
                            token_upper = str(token).upper() if token else ''
                            logger.warning(f"[prime_candles] Looking up token_upper='{token_upper}' in mcx_map, keys={list(mcx_map.keys())[:5]}")
                            if token_upper in mcx_map:
                                mcx_entry = mcx_map[token_upper]
                                # mcx_entry format: [symbol, tsym, lot, expiry, token]
                                numeric_token = str(mcx_entry[4]) if len(mcx_entry) > 4 else None
                                trading_symbol = mcx_entry[1] if len(mcx_entry) > 1 else None
                                exch = 'MCX'  # It's an MCX instrument
                                logger.trace(f"[{self.__class__.__name__}.prime_candles] - MCX: {token} -> {trading_symbol} (token: {numeric_token}) from futures_map")
                            else:
                                # FIX: Also check if token matches trading symbol (e.g., "GOLDTEN31MAR26", "MCXBULLDEX24MAR26")
                                for short_sym, mcx_entry in mcx_map.items():
                                    if isinstance(mcx_entry, list) and len(mcx_entry) > 1:
                                        if isinstance(token, str) and isinstance(mcx_entry[1], str) and mcx_entry[1].upper() == token.upper():
                                            numeric_token = str(mcx_entry[4]) if len(mcx_entry) > 4 else None
                                            trading_symbol = mcx_entry[1] if len(mcx_entry) > 1 else None
                                            exch = 'MCX'
                                            logger.trace(f"[{self.__class__.__name__}.prime_candles] - MCX: {token} -> {trading_symbol} (token: {numeric_token}) via trading symbol match")
                                            break
                        except Exception as e:
                            logger.warning(f"[{self.__class__.__name__}.prime_candles] - Failed to load MCX futures_map: {e}")
                    
                    # Fallback to old prefix matching logic if mcx_futures_map lookup failed
                    if not numeric_token:
                        # Step 1: Use TOKEN_TO_SYMBOL for prefix matching to find trading symbol
                        for tok, tsym in self.master.TOKEN_TO_SYMBOL.items():
                            if isinstance(tsym, str) and isinstance(token, str) and tsym.upper().startswith(token.upper()):
                                logger.trace(f"[{self.__class__.__name__}.prime_candles] - Found trading symbol: {tsym}")
                                trading_symbol = tsym
                                break
                        
                        # Step 2: Use SYMBOL_TO_TOKEN to get numeric token from trading symbol
                        if trading_symbol:
                            numeric_token = self.master.SYMBOL_TO_TOKEN.get(trading_symbol)
                            if numeric_token:
                                logger.trace(f"[{self.__class__.__name__}.prime_candles] - Resolved {token} -> numeric token {numeric_token}")
                            else:
                                # Symbol not found in mcx_futures_map, keep numeric_token as None
                                pass
                    
                    if numeric_token:
                        token = numeric_token
                    elif token and isinstance(token, str) and token.isdigit():
                        # Token is already numeric, keep it
                        pass
                    else:
                        # Token is a symbol name (non-numeric), try to resolve
                        token = self.get_token(token)
                    
                    key = f"{exch}|{token}"
                elif '|' in str(item):
                    key = item
                else:
                    token = self.get_token(item)
                    exch = 'MCX' if self.segment_name == 'mcx' else 'NSE'
                    key = f"{exch}|{token}"
                
                ex, tk = key.split('|')
                # Get interval from strategy parameters, default to 5 minutes
                interval = self._priming_interval if hasattr(self, '_priming_interval') else 5
                logger.warning(f"[prime_candles] Using key: {key}, token before resolution: {token}")
                res = self.api.get_time_price_series(
                    exchange=ex,
                    token=tk, 
                    starttime=start_dt.timestamp(), 
                    endtime=end_dt.timestamp(), 
                    interval=interval
                )
                
                if res and isinstance(res, list):
                    if key not in self.SYMBOLDICT:
                        sym = self.get_symbol(tk, exchange=ex)
                        self.SYMBOLDICT[key] = {
                            'symbol': sym, 't': sym, 'company_name': self.get_company_name(tk, exchange=ex),
                            'token': tk, 'exchange': ex, 'ltp': float(res[-1]['intc']),
                            'high': float(res[-1].get('inth', 0)), 'low': float(res[-1].get('intl', 0)), 
                            'volume': int(res[-1].get('v', 0))
                        }
                    
                    self.SYMBOLDICT[key]['candles'] = res
                    success_count += 1
                    logger.debug(f"[{self.__class__.__name__}.prime_candles] - Primed {key} with {len(res)} candles. Last: {res[-1].get('intc', '?')}")
                else:
                    logger.warning(f"[{self.__class__.__name__}.prime_candles] - No history returned for {key}. Live feed will populate data.")
                
                # Add a small delay to avoid rate limiting
                import time
                time.sleep(0.1)
            except Exception as e:
                logger.warning(f"[{self.__class__.__name__}.prime_candles] - Failed to prime {item}: {e}")
        
        print(f"✅ Primed {success_count}/{len(symbols)} symbols successfully.")
        
        # Summary: log bar counts for all symbols
        for item in symbols:
            try:
                token = item.get('token') if isinstance(item, dict) else item
                exch = item.get('exchange', 'MCX') if isinstance(item, dict) else 'MCX'
                key = f"{exch}|{token}" if '|' not in str(token) else token
                sym_data = self.SYMBOLDICT.get(key, {})
                candles = sym_data.get('candles', [])
                if len(candles) < 10:
                    logger.warning(f"[{self.__class__.__name__}.prime_candles] - {key} has only {len(candles)} candles (need 12+ for indicators)")
            except:
                pass

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
    def get_ltp(self, key): 
        logger.trace(f"[{self.__class__.__name__}.get_ltp] - Getting LTP for key: {key}")
        return self.SYMBOLDICT.get(key, {}).get('ltp')
    def get_dk_levels(self, key): 
        logger.trace(f"[{self.__class__.__name__}.get_dk_levels] - Getting DK levels for key: {key}")
        d = self.SYMBOLDICT.get(key, {})
        return {'ltp': d.get('ltp', 0), 'high': d.get('h', 0), 'low': d.get('l', 0)}

    def get_near_future(self, symbol, exchange='NFO'): 
        logger.debug(f"[{self.__class__.__name__}.get_near_future] - Getting near future for symbol: {symbol}, exchange: {exchange}")
        return self.resolver.get_near_future(symbol, exchange, self.api)
    def get_credit_spread_contracts(self, symbol, ltp, side, hedge_steps=4, expiry_type="monthly", instrument="OPTSTK"):
        logger.debug(f"[{self.__class__.__name__}.get_credit_spread_contracts] - Getting credit spread contracts for symbol: {symbol}, ltp: {ltp}, side: {side}")
        return self.resolver.get_credit_spread_contracts(symbol, ltp, side, hedge_steps, expiry_type, instrument)
    
    def get_option_ltp_by_symbol(self, tsym):
        logger.debug(f"[{self.__class__.__name__}.get_option_ltp_by_symbol] - Getting option LTP by symbol: {tsym}")
        if self.segment_name == 'mcx':
            logger.trace(f"[{self.__class__.__name__}.get_option_ltp_by_symbol] - MCX segment, looking for futures only.")
            for k, v in self.SYMBOLDICT.items():
                if v.get('symbol') == tsym: 
                    logger.trace(f"[{self.__class__.__name__}.get_option_ltp_by_symbol] - Found LTP in SYMBOLDICT: {v.get('ltp')}")
                    return v.get('ltp')
        
        for r in self.master.DERIVATIVE_OPTIONS:
            if r.get('tradingsymbol') == tsym:
                logger.trace(f"[{self.__class__.__name__}.get_option_ltp_by_symbol] - Found derivative option, fetching quotes.")
                success, q = self._handle_api_call(self.api.get_quotes, exchange=r['exchange'], token=r['token'])
                if success and q:
                    return float(q.get('lp') or q.get('ltp') or 0)
                return None
        logger.debug(f"[{self.__class__.__name__}.get_option_ltp_by_symbol] - LTP not found for {tsym}.")
        return None

