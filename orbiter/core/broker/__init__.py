import os
import logging
import json
import traceback # Import traceback
from typing import Dict, Optional, Any, List
from .connection import ConnectionManager
from .master import ScripMaster
from .resolver import ContractResolver
from .margin import MarginCalculator
# Import executor - use margin-aware if paper trade
import os
paper_trade = os.environ.get("ORBITER_PAPER_TRADE", "true").lower() == "true"
if paper_trade:
    try:
        from orbiter.utils.margin.margin_executor import MarginAwareExecutor
        ExecutorClass = MarginAwareExecutor
        print("[MARGIN] Using MarginAwareExecutor (paper trade mode)")
    except ImportError:
        from .executor import OrderExecutor
        ExecutorClass = OrderExecutor
else:
    from .executor import OrderExecutor
    ExecutorClass = OrderExecutor
# Original: from .executor import OrderExecutor
from orbiter.utils.constants_manager import ConstantsManager

logger = logging.getLogger("ORBITER")

class BrokerClient:
    """
    🚀 Central Gateway for Shoonya API Interactions.
    """
    _MASTERS: Dict[str, ScripMaster] = {}  # Segment-aware Masters

    def __init__(self, project_root: str = None, config_path: str = '../cred.yml', segment_name: str = 'nfo'):
        logger.debug(f"[{self.__class__.__name__}.__init__] - Initializing BrokerClient for segment: {segment_name}")
        if project_root is None:
            # repo_root/orbiter/core/broker/__init__.py -> repo_root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.project_root = project_root
        self.segment_name = segment_name.lower()
        self.constants = ConstantsManager.get_instance()
        self.conn = ConnectionManager(config_path)
        
        if self.segment_name not in BrokerClient._MASTERS:
            BrokerClient._MASTERS[self.segment_name] = ScripMaster(project_root)
            logger.debug(f"[{self.__class__.__name__}.__init__] - Initialized ScripMaster for segment: {self.segment_name.upper()}")
        
        self.master = BrokerClient._MASTERS[self.segment_name]
        self.resolver = ContractResolver(self.master, api=self.conn.api)
        self.margin = MarginCalculator(self.master)
        
        # 🛡️ Load Execution Policy for the segment
        from orbiter.utils.data_manager import DataManager
        exch_config = DataManager.load_config(project_root, 'mandatory_files', 'exchange_config')
        self.exchange_config = exch_config  # Store full config for access by action executors
        policy = exch_config.get(self.segment_name, {}).get('execution_policy', {})
        
        # Only pass paper_trade when using MarginAwareExecutor
        if paper_trade:
            self.executor = ExecutorClass(self.conn.api, self._init_logger(), execution_policy=policy, paper_trade=paper_trade)
        else:
            self.executor = ExecutorClass(self.conn.api, self._init_logger(), execution_policy=policy)
        logger.debug(f"[{self.__class__.__name__}.__init__] - Resolver, Margin, Executor (with policy) initialized.")
        
        self.SYMBOLDICT: Dict[str, Dict[str, Any]] = {}
        self.span_cache_path = None
        self._span_cache = None
        self._tick_callbacks = []

    def register_tick_callback(self, callback):
        """Register a callback to be called on every tick."""
        self._tick_callbacks.append(callback)
        logger.debug(f"Registered tick callback: {callback.__name__}")
        self._priming_interval = 5  # Default 5-min candles
        
        # Download appropriate scrip master based on segment
        if self.segment_name == 'mcx':
            exchange = 'MCX'
        elif self.segment_name == 'bfo':
            exchange = 'BFO'
        else:
            exchange = 'NFO'
        self.download_scrip_master(exchange)
        logger.debug(f"[{self.__class__.__name__}.__init__] - Scrip master downloaded for segment: {self.segment_name.upper()}")
        
        self.load_symbol_mapping()
        logger.debug(f"[{self.__class__.__name__}.__init__] - Symbol mappings loaded.")


    def _init_logger(self):
        log_dir = os.path.join(self.project_root, 'logs', self.segment_name)
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, 'trade_calls.log')
        
        logger = logging.getLogger(f"trade_calls_{self.segment_name}")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            h = logging.FileHandler(path)
            h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
            logger.addHandler(h)
        return logger

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
    
    @property
    def span_cache(self): 
        return self._span_cache if self._span_cache is not None else {}

    def login(self, factor2_override=None): 
        logger.debug(f"[{self.__class__.__name__}.login] - Attempting broker login.")
        result = self.conn.login(factor2_override)
        if result:
            logger.info(f"[{self.__class__.__name__}.login] - Broker login successful.")
        else:
            logger.error(f"[{self.__class__.__name__}.login] - Broker login failed.")
        return result

    def start_live_feed(self, symbols):
        logger.debug(f"[{self.__class__.__name__}.start_live_feed] - Starting live feed for {len(symbols)} symbols.")
        logger.trace(f"[{self.__class__.__name__}.start_live_feed] - Input symbols: {symbols[:3]}...")
        
        # Resolve symbols to tokens if needed (for MCX, symbols may be names like "GOLDTEN" not numeric tokens)
        mcx_futures_map = None
        nfo_futures_map = None
        
        # Load MCX futures map
        mcx_futures_map_path = os.path.join(self.project_root, 'orbiter', 'data', 'mcx_futures_map.json')
        if os.path.exists(mcx_futures_map_path):
            try:
                with open(mcx_futures_map_path, 'r') as f:
                    mcx_futures_map = json.load(f)
                logger.trace(f"[{self.__class__.__name__}.start_live_feed] - Loaded {len(mcx_futures_map)} MCX futures mappings")
            except Exception as e:
                logger.warning(f"[{self.__class__.__name__}.start_live_feed] - Failed to load MCX futures_map: {e}")
        
        # Load NFO futures map
        nfo_futures_map_path = os.path.join(self.project_root, 'orbiter', 'data', 'nfo_futures_map.json')
        if os.path.exists(nfo_futures_map_path):
            try:
                with open(nfo_futures_map_path, 'r') as f:
                    nfo_futures_map = json.load(f)
                logger.trace(f"[{self.__class__.__name__}.start_live_feed] - Loaded {len(nfo_futures_map)} NFO futures mappings")
            except Exception as e:
                logger.warning(f"[{self.__class__.__name__}.start_live_feed] - Failed to load NFO futures_map: {e}")

        def resolve_to_token(token_or_symbol, exchange):
            """Resolve symbol name to numeric token if needed."""
            # If already numeric, return as-is
            # CRITICAL: Handle non-string inputs (dicts, etc.)
            if not isinstance(token_or_symbol, str):
                logger.warning(f"Non-string input {type(token_or_symbol)}, returning as-is")
                return str(token_or_symbol) if token_or_symbol else ""

            if isinstance(token_or_symbol, str) and token_or_symbol.isdigit():
                return token_or_symbol
            
            # FIX: Check MCX futures_map first for symbol names like GOLD, ALUMINI, etc.
            # Also check trading symbols like "GOLD31MAR26", "MCXBULLDEX24MAR26", etc.
            if isinstance(token_or_symbol, str) and mcx_futures_map and token_or_symbol.upper() in mcx_futures_map:
                mcx_entry = mcx_futures_map[token_or_symbol.upper()]
                numeric_token = str(mcx_entry[4]) if len(mcx_entry) > 4 else None
                if numeric_token:
                    logger.trace(f"[{self.__class__.__name__}.resolve_to_token] - Resolved MCX {token_or_symbol} -> {numeric_token} via futures_map")
                    return numeric_token
            
            # FIX: Also check if token matches trading symbol (e.g., "GOLDTEN31MAR26", "MCXBULLDEX24MAR26")
            if mcx_futures_map:
                for short_sym, mcx_entry in mcx_futures_map.items():
                    if isinstance(mcx_entry, list) and len(mcx_entry) > 1:
                        if isinstance(mcx_entry[1], str) and mcx_entry[1].upper() == token_or_symbol.upper():
                            numeric_token = str(mcx_entry[4]) if len(mcx_entry) > 4 else None
                            if numeric_token:
                                logger.trace(f"[{self.__class__.__name__}.resolve_to_token] - Resolved MCX trading symbol {token_or_symbol} -> {numeric_token} via futures_map")
                                return numeric_token
            
            # FIX: Check NFO futures_map for symbol names like NIFTY, BANKNIFTY, etc.
            if nfo_futures_map:
                # Check if token is in map (key is numeric token, value is [symbol, trading_symbol])
                for num_token, entry in nfo_futures_map.items():
                    if isinstance(entry, list) and len(entry) >= 2:
                        if (isinstance(entry[0], str) and entry[0].upper() == token_or_symbol.upper()) or (isinstance(entry[1], str) and entry[1].upper() == token_or_symbol.upper()):
                            logger.trace(f"[{self.__class__.__name__}.resolve_to_token] - Resolved NFO {token_or_symbol} -> {num_token} via futures_map")
                            return num_token
            
            # Try to resolve using broker's symbol-to-token mapping
            resolved = self.master.SYMBOL_TO_TOKEN.get(token_or_symbol.upper()) if isinstance(token_or_symbol, str) else None
            if resolved:
                logger.trace(f"[{self.__class__.__name__}.resolve_to_token] - Resolved {token_or_symbol} -> {resolved}")
                return resolved
            # Try with trading symbol prefix (e.g., "GOLDTEN31MAR26" -> "GOLDTEN")
            for tok, tsym in self.master.TOKEN_TO_SYMBOL.items():
                if isinstance(tsym, str) and isinstance(token_or_symbol, str) and tsym.upper().startswith(token_or_symbol.upper()):
                    logger.trace(f"[{self.__class__.__name__}.resolve_to_token] - Resolved {token_or_symbol} via prefix -> {tok}")
                    return tok
            logger.warning(f"[{self.__class__.__name__}.resolve_to_token] - Could not resolve {token_or_symbol}, using as-is")
            return token_or_symbol
        
        # Pre-process symbols to resolve token names to numeric tokens
        resolved_symbols = []
        for s in symbols:
            if isinstance(s, dict):
                tk = str(s.get('token'))
                ex = s.get('exchange', 'NSE')
                # Resolve token if not numeric
                resolved_tk = resolve_to_token(tk, ex)
                if resolved_tk != tk:
                    logger.debug(f"[{self.__class__.__name__}.start_live_feed] - Token resolved: {tk} -> {resolved_tk}")
                resolved_symbols.append({**s, 'token': resolved_tk})
            else:
                # Plain symbol - keep as-is, connection manager will handle
                resolved_symbols.append(s)
        
        def _tick_handler(msg, tk, ex):
            key = f"{ex}|{tk}"
            sym = self.get_symbol(tk, exchange=ex)
            
            existing_data = self.SYMBOLDICT.get(key, {})
            existing_candles = existing_data.get('candles', [])
            
            # 🔥 Real-time Candle population: Convert tick to a pseudo-candle if no history exists yet
            if not existing_candles:
                pseudo_candle = {
                    'stat': 'Ok', # 🔥 Critical for FactConverter
                    'time': msg.get('t', '00-00-0000 00:00:00'),
                    'into': msg['lp'], 'inth': msg.get('h', msg['lp']), 
                    'intl': msg.get('l', msg['lp']), 'intc': msg['lp'],
                    'v': msg.get('v', '0'), 'ssboe': msg.get('ssboe', '0')
                }
                existing_candles = [pseudo_candle]
            else:
                # Update last candle's close with newest LTP
                existing_candles[-1]['intc'] = msg['lp']
                if float(msg.get('h', 0)) > float(existing_candles[-1]['inth']): existing_candles[-1]['inth'] = msg['h']
                if float(msg.get('l', 0)) < float(existing_candles[-1]['intl']) and float(msg.get('l', 0)) > 0: existing_candles[-1]['intl'] = msg['l']

            tick_data = {
                **msg, 'symbol': sym, 't': sym, 'company_name': self.get_company_name(tk, exchange=ex),
                'token': tk, 'exchange': ex, 'ltp': float(msg['lp']),
                'high': float(msg.get('h', 0)), 'low': float(msg.get('l', 0)), 'volume': int(msg.get('v', 0)),
                'candles': existing_candles
            }
            # Store at token key (e.g., MCX|477176)
            self.SYMBOLDICT[key] = tick_data
            
            # Store at full trading symbol key (e.g., MCX|GOLDTEN31MAR26)
            full_symbol = sym.split('|')[-1] if '|' in sym else sym
            if f"{ex}|{full_symbol}" != key:
                self.SYMBOLDICT[f"{ex}|{full_symbol}"] = tick_data
            
            # Also store at short symbol key (e.g., MCX|GOLDTEN) for instrument lookup
            # Extract short symbol by removing expiry suffix like 31MAR26, 26MAR26, etc.
            import re
            short_symbol = re.sub(r'\d{2}[A-Z]{3}\d{2}(FC|F)?$', '', full_symbol)
            if short_symbol != full_symbol and f"{ex}|{short_symbol}" != key:
                self.SYMBOLDICT[f"{ex}|{short_symbol}"] = tick_data
                logger.trace(f"[{self.__class__.__name__}._tick_handler] - Stored tick at keys: {key}, {ex}|{full_symbol}, {ex}|{short_symbol}")
            logger.trace(f"[{self.__class__.__name__}._tick_handler] - Received tick for {sym}: {msg}")
            
            # Notify registered callbacks
            for callback in self._tick_callbacks:
                try:
                    callback(sym, tick_data)
                except Exception as e:
                    logger.error(f"Tick callback error: {e}")
        self.conn.start_live_feed(resolved_symbols, _tick_handler)
        logger.info(f"[{self.__class__.__name__}.start_live_feed] - Live feed started for {len(symbols)} symbols.")

    def prime_candles(self, symbols: List[Any], lookback_mins: int = 120):
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
                    exch = item.get('exchange', 'NSE')
                else:
                    # item is a string (symbol name)
                    token = item
                
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
    
    def set_span_cache_path(self, path): 
        logger.trace(f"[{self.__class__.__name__}.set_span_cache_path] - Setting span cache path to: {path}")
        self.span_cache_path = path

    def load_span_cache(self):
        logger.debug(f"[{self.__class__.__name__}.load_span_cache] - Loading span cache from: {self.span_cache_path}")
        if not self.span_cache_path: 
            logger.debug(f"[{self.__class__.__name__}.load_span_cache] - Span cache path not set.")
            return
        try:
            if os.path.exists(self.span_cache_path):
                with open(self.span_cache_path, 'r') as f:
                    self._span_cache = json.load(f)
                logger.debug(f"[{self.__class__.__name__}.load_span_cache] - Span cache loaded successfully.")
            else: 
                self._span_cache = {}
                logger.debug(f"[{self.__class__.__name__}.load_span_cache] - Span cache file not found, initializing empty cache.")
        except Exception as e: 
            self._span_cache = {}
            logger.error(f"[{self.__class__.__name__}.load_span_cache] - Failed to load span cache: {e}. Traceback: {traceback.format_exc()}")

    def save_span_cache(self):
        logger.debug(f"[{self.__class__.__name__}.save_span_cache] - Saving span cache to: {self.span_cache_path}")
        if not self.span_cache_path or self._span_cache is None: 
            logger.debug(f"[{self.__class__.__name__}.save_span_cache] - Span cache path not set or cache is empty. Skipping save.")
            return
        try:
            os.makedirs(os.path.dirname(self.span_cache_path), exist_ok=True)
            with open(self.span_cache_path, 'w') as f:
                json.dump(self._span_cache, f)
            logger.debug(f"[{self.__class__.__name__}.save_span_cache] - Span cache saved successfully.")
        except Exception as e: 
            logger.error(f"[{self.__class__.__name__}.save_span_cache] - Failed to save span cache: {e}. Traceback: {traceback.format_exc()}")

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
    def calculate_span_for_spread(self, spread, product_type="I", haircut=0.20):
        logger.debug(f"[{self.__class__.__name__}.calculate_span_for_spread] - Calculating span for spread: {spread}")
        return self.margin.calculate_span_for_spread(spread, self.api, self.conn.cred['user'], product_type, haircut)
    
    def calculate_future_margin(self, future_details, product_type="I", haircut=0.20):
        logger.debug(f"[{self.__class__.__name__}.calculate_future_margin] - Calculating future margin for: {future_details}")
        return self.margin.calculate_future_margin(future_details, self.api, self.conn.cred['user'], product_type, haircut)
    
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
                q = self.api.get_quotes(exchange=r['exchange'], token=r['token'])
                return float(q.get('lp') or q.get('ltp') or 0) if q else None
        logger.debug(f"[{self.__class__.__name__}.get_option_ltp_by_symbol] - LTP not found for {tsym}.")
        return None

    def place_put_credit_spread(self, **kwargs):
        logger.debug(f"[{self.__class__.__name__}.place_put_credit_spread] - Placing PUT credit spread with kwargs: {kwargs}")
        logger.trace(f"🔭 [Broker.place_put_credit_spread] symbol={kwargs.get('symbol')}, ltp={kwargs.get('ltp')}")
        res = self.resolver.get_credit_spread_contracts(kwargs['symbol'], kwargs['ltp'], 'PUT', kwargs['hedge_steps'], kwargs['expiry_type'], kwargs['instrument'])
        if not res.get('ok'): 
            logger.error(f"[{self.__class__.__name__}.place_put_credit_spread] - Failed to get credit spread contracts: {res.get('reason')}")
            return res
        return self.executor.place_spread(res, kwargs['execute'], kwargs['product_type'], kwargs['price_type'])

    def place_call_credit_spread(self, **kwargs):
        logger.debug(f"[{self.__class__.__name__}.place_call_credit_spread] - Placing CALL credit spread with kwargs: {kwargs}")
        logger.trace(f"🔭 [Broker.place_call_credit_spread] symbol={kwargs.get('symbol')}, ltp={kwargs.get('ltp')}")
        res = self.resolver.get_credit_spread_contracts(kwargs['symbol'], kwargs['ltp'], 'CALL', kwargs['hedge_steps'], kwargs['expiry_type'], kwargs['instrument'])
        if not res.get('ok'): 
            logger.error(f"[{self.__class__.__name__}.place_call_credit_spread] - Failed to get credit spread contracts: {res.get('reason')}")
            return res
        return self.executor.place_spread(res, kwargs['execute'], kwargs['product_type'], kwargs['price_type'])

    def get_limits(self):
        logger.debug(f"[{self.__class__.__name__}.get_limits] - Fetching limits from broker.")
        try:
            setattr(self.api, '_NorenApi__username', self.conn.cred['user'])
            setattr(self.api, '_NorenApi__accountid', self.conn.cred['user'])
            token = getattr(self.api, '_NorenApi__susertoken', None)
            setattr(self.api, '_NorenApi__susertoken', token)

            res = self.api.get_limits()
            if not res or res.get('stat') != 'Ok':
                logger.warning(f"[{self.__class__.__name__}.get_limits] - Broker did not return OK status for limits: {res}")
                return None
            
            cash = float(res.get('cash', 0))
            collateral = float(res.get('collateral', 0))
            used = float(res.get('marginused', 0))
            total_power = cash + collateral
            
            limits_data = {
                'liquid_cash': cash,              
                'collateral_value': collateral,   
                'margin_used': used,              
                'total_power': total_power,       
                'available': total_power - used,  
                'payin': float(res.get('payin', 0))
            }
            logger.debug(f"[{self.__class__.__name__}.get_limits] - Limits fetched: {limits_data}")
            return limits_data
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}.get_limits] - Error fetching limits: {e}. Traceback: {traceback.format_exc()}")
            return None

    def get_positions(self):
        logger.debug(f"[{self.__class__.__name__}.get_positions] - Fetching positions from broker.")
        try:
            setattr(self.api, '_NorenApi__username', self.conn.cred['user'])
            setattr(self.api, '_NorenApi__accountid', self.conn.cred['user'])
            token = getattr(self.api, '_NorenApi__susertoken', None)
            setattr(self.api, '_NorenApi__susertoken', token)
            
            res = self.api.get_positions()
            if not res: 
                logger.debug(f"[{self.__class__.__name__}.get_positions] - No positions returned by broker.")
                return []
            ok_positions = [p for p in res if p.get('stat') == 'Ok']
            logger.debug(f"[{self.__class__.__name__}.get_positions] - {len(ok_positions)} 'Ok' positions fetched.")
            logger.trace(f"[{self.__class__.__name__}.get_positions] - Raw positions: {res}")
            return ok_positions
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}.get_positions] - Error fetching positions: {e}. Traceback: {traceback.format_exc()}")
            return []

    def get_order_history(self):
        logger.debug(f"[{self.__class__.__name__}.get_order_history] - Fetching order history from broker.")
        try:
            res = self.api.get_order_book()
            if not res: 
                logger.debug(f"[{self.__class__.__name__}.get_order_history] - No order history returned by broker.")
                return []
            ok_orders = [o for o in res if o.get('stat') == 'Ok']
            logger.debug(f"[{self.__class__.__name__}.get_order_history] - {len(ok_orders)} 'Ok' orders fetched.")
            logger.trace(f"[{self.__class__.__name__}.get_order_history] - Raw order book: {res}")
            return ok_orders
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}.get_order_history] - Error fetching order history: {e}. Traceback: {traceback.format_exc()}")
            return []

    def place_future_order(self, **kwargs):
        logger.debug(f"[{self.__class__.__name__}.place_future_order] - Preparing to place future order with kwargs: {kwargs}")
        symbol, exchange = kwargs['symbol'], kwargs.get('exchange', 'NFO')
        res = self.resolver.get_near_future(symbol, exchange, self.api)
        
        if not res and kwargs.get('token'):
            token_in = str(kwargs.get('token'))
            tsym = self.master.TOKEN_TO_SYMBOL.get(token_in)
            if tsym:
                res = {'token': token_in, 'tsym': tsym}
                logger.debug(f"[{self.__class__.__name__}.place_future_order] - Resolved via Map: {token_in} -> {tsym}")

        if not res: 
            logger.error(f"[{self.__class__.__name__}.place_future_order] - Future contract not found for {symbol}.")
            return {'ok': False, 'reason': 'future_not_found'}
        
        lot_size = 0
        
        if hasattr(self, 'SYMBOLDICT'):
            live_data = self.SYMBOLDICT.get(res['token'])
            if live_data and live_data.get('ls'):
                lot_size = int(live_data['ls'])
                logger.trace(f"[{self.__class__.__name__}.place_future_order] - Found lot size in Live Feed: {lot_size}")

                if lot_size <= 0:
                    tok_id = str(res['token'].split("|")[-1])
                    cached_ls = self.master.TOKEN_TO_LOTSIZE.get(tok_id)
                    if cached_ls:
                        lot_size = cached_ls
                        logger.trace(f"[{self.__class__.__name__}.place_future_order] - Found lot size in Memory Cache: {lot_size}")
        
        if lot_size <= 0:
            tsym = res.get('tsym') or res.get('tradingsymbol')
            for r in self.master.DERIVATIVE_OPTIONS:
                if r.get('tradingsymbol') == tsym:
                    lot_size = int(r.get('lotsize', 0))
                    break
        
        if lot_size <= 0: 
            tsym = res.get('tsym') or res.get('tradingsymbol')
            logger.error(f"[{self.__class__.__name__}.place_future_order] - Invalid lot size for {tsym}.")
            return {'ok': False, 'reason': 'invalid_lot_size'}
        
        tsym = res.get('tsym') or res.get('tradingsymbol')
        details = {'tsym': tsym, 'lot_size': lot_size, 'exchange': exchange, 'token': res.get('token', '')}
        logger.debug(f"[{self.__class__.__name__}.place_future_order] - Future order details resolved: {details}")
        return self.executor.place_future_order(details, kwargs['side'], kwargs['execute'], kwargs['product_type'], kwargs['price_type'])

    def get_option_theta(self, symbol: str, expiry_date: str, strike_price: float, option_type: str) -> Optional[float]:
        """Fetches the Theta value for a given option contract."""
        logger.debug(f"[{self.__class__.__name__}.get_option_theta] - Fetching Theta for {symbol}, Expiry: {expiry_date}, Strike: {strike_price}, Type: {option_type}")
        try:
            # Parameters for API call need to be precise. Assuming some common ones.
            # 'InterestRate' and 'Volatility' might need defaults or fetching from config.
            ret = self.api.option_greek(
                expiredate=expiry_date,
                StrikePrice=str(strike_price),
                SpotPrice=str(self.get_ltp(f"{self.segment_name.upper()}|{self.get_token(symbol)}") or 0.0), # Use current LTP or default
                InterestRate='10', # Placeholder, might need dynamic fetching
                Volatility='20',   # Placeholder, might need dynamic fetching
                OptionType=option_type.upper() # CE or PE
            )
            
            if ret and ret.get('stat') == 'Ok':
                theta = float(ret.get('theta', 0.0)) # Default to 0.0 if 'theta' key not found
                logger.debug(f"[{self.__class__.__name__}.get_option_theta] - Fetched Theta: {theta}")
                return theta
            else:
                logger.warning(f"[{self.__class__.__name__}.get_option_theta] - API call returned non-OK status or missing data: {ret}")
                return None
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}.get_option_theta] - Error fetching option greek: {e}. Traceback: {traceback.format_exc()}")
            return None
