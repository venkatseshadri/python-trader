#!/usr/bin/env python3
"""
Mock Broker Client - Replays recorded data for testing Orbiter off-hours

Usage:
    python -m orbiter.main --paper_trade=true --mock_data=true --strategyCode=n1
    
Or with custom data file:
    python -m orbiter.main --paper_trade=true --mock_data=true --mock_data_file=/path/to/data.json --strategyCode=n1
"""
import os
import json
import logging
import time
from typing import Dict, Optional, Any, List, Callable
from pathlib import Path

logger = logging.getLogger("ORBITER")


class MockBrokerClient:
    """
    Mock BrokerClient that replays pre-recorded candle/tick data.
    Used for testing Orbiter outside market hours.
    """
    
    _DEFAULT_DATA_FILES = {
        'nfo': '/root/.openclaw/agents/main/workspace/memory/OrbiterTestData/nfo_data.json',
        'bfo': '/root/.openclaw/agents/main/workspace/memory/OrbiterTestData/bfo_data.json',
        'mcx': '/root/.openclaw/agents/main/workspace/memory/OrbiterTestData/mcx_data.json',
    }
    
    _LOCAL_DATA_FILES = {
        'nfo': 'orbiter/test_data/nfo_data.json',
        'bfo': 'orbiter/test_data/bfo_data.json',
        'mcx': 'orbiter/test_data/mcx_data.json',
    }
    
    def __init__(self, project_root: str = None, config_path: str = None, segment_name: str = 'nfo'):
        self.project_root = project_root or os.getcwd()
        self.segment_name = segment_name.lower()
        self.constants = None
        self.SYMBOLDICT: Dict[str, Dict[str, Any]] = {}
        self._tick_callbacks = []
        self._priming_interval = 5
        self._data_file = None
        self._candle_data = {}
        self._replay_index = 0
        self._replaying = False
        
        # Add mock resolver and master for compatibility
        self.resolver = MockResolver()
        self.master = MockMaster()
        
        self._load_data()
        self._init_constants()
    
    def _init_constants(self):
        """Initialize constants manager"""
        from orbiter.utils.constants_manager import ConstantsManager
        self.constants = ConstantsManager.get_instance()
    
    def _load_data(self):
        """Load recorded data from JSON file"""
        # Priority: env var > default location > local project location
        custom_file = os.environ.get('ORBITER_MOCK_DATA_FILE')
        if custom_file and os.path.exists(custom_file):
            self._data_file = custom_file
            logger.info(f"MockBrokerClient: Using custom data file from env: {self._data_file}")
        else:
            default_file = self._DEFAULT_DATA_FILES.get(self.segment_name, self._DEFAULT_DATA_FILES['nfo'])
            if os.path.exists(default_file):
                self._data_file = default_file
                logger.info(f"MockBrokerClient: Using default data file: {self._data_file}")
            else:
                # Try local project directory
                local_file = self._LOCAL_DATA_FILES.get(self.segment_name)
                if local_file:
                    full_local = os.path.join(self.project_root, local_file)
                    if os.path.exists(full_local):
                        self._data_file = full_local
                        logger.info(f"MockBrokerClient: Using local data file: {self._data_file}")
        
        if not self._data_file:
            logger.warning(f"MockBrokerClient: No data file found. Using synthetic data.")
            return
        
        try:
            with open(self._data_file, 'r') as f:
                data = json.load(f)
            
            # Parse candle format data
            for symbol, info in data.items():
                if isinstance(info, dict) and 'candles' in info:
                    exchange = info.get('exchange', 'NSE')
                    token = info.get('token', '')
                    candles = info.get('candles', [])
                    
                    key = f"{exchange}|{token}"
                    self._candle_data[key] = {
                        'symbol': symbol,
                        'token': token,
                        'exchange': exchange,
                        'candles': candles
                    }
                    
                    # Also store by symbol name
                    short_symbol = symbol.split('_')[-1] if '_' in symbol else symbol
                    self._candle_data[f"{exchange}|{short_symbol}"] = self._candle_data[key]
                    self._candle_data[short_symbol] = self._candle_data[key]
            
            logger.info(f"MockBrokerClient: Loaded {len(self._candle_data)} instruments from {self._data_file}")
        except Exception as e:
            logger.error(f"MockBrokerClient: Failed to load data: {e}")
            self._candle_data = {}
    
    def register_tick_callback(self, callback: Callable):
        """Register a callback to be called on every tick."""
        self._tick_callbacks.append(callback)
        logger.debug(f"MockBrokerClient: Registered tick callback: {callback.__name__}")
    
    def load_symbol_mapping(self):
        """No-op for mock - just satisfy interface"""
        pass
    
    def download_scrip_master(self, exchange: str):
        """No-op for mock - just satisfy interface"""
        pass
    
    def start_live_feed(self, symbols: List[Any], on_tick_callback: Callable = None, verbose: bool = False):
        """
        Simulate live feed by replaying candle data as ticks.
        """
        logger.info(f"MockBrokerClient: Starting live feed for {len(symbols)} symbols...")
        
        callback = on_tick_callback or (self._tick_callbacks[0] if self._tick_callbacks else None)
        if not callback:
            logger.warning("MockBrokerClient: No callback provided for live feed")
            return
        
        self._replaying = True
        
        # Flatten all candles into chronological list
        all_candles = []
        for symbol in symbols:
            symbol_key = f"NSE|{symbol}" if '|' not in str(symbol) else symbol
            
            for key, info in self._candle_data.items():
                if symbol.upper() in key.upper() or symbol in info.get('symbol', '').upper():
                    for candle in info.get('candles', []):
                        all_candles.append({
                            'candle': candle,
                            'symbol': info.get('symbol', key),
                            'token': info.get('token', ''),
                            'exchange': info.get('exchange', 'NSE'),
                            'time': candle.get('time', '')
                        })
        
        # Sort by time
        all_candles.sort(key=lambda x: x['time'])
        
        logger.info(f"MockBrokerClient: Replaying {len(all_candles)} candles...")
        
        for item in all_candles:
            if not self._replaying:
                break
                
            candle = item['candle']
            ltp = float(candle.get('intc', 0))
            
            # Build tick message
            tick_msg = {
                'lp': ltp,
                'last_price': ltp,
                'o': float(candle.get('into', 0)),
                'h': float(candle.get('inth', 0)),
                'l': float(candle.get('intl', 0)),
                'c': ltp,
                'v': candle.get('intv', '0'),
                'oi': candle.get('oi', '0'),
                'time': candle.get('time', ''),
                'ssboe': candle.get('ssboe', '0')
            }
            
            # Update SYMBOLDICT
            key = f"{item['exchange']}|{item['token']}"
            sym = item['symbol']
            self.SYMBOLDICT[key] = {
                'symbol': sym,
                't': sym,
                'token': item['token'],
                'exchange': item['exchange'],
                'ltp': ltp,
                'high': tick_msg['h'],
                'low': tick_msg['l'],
                'volume': int(candle.get('intv', 0)),
                'candles': [candle]
            }
            
            # Call callbacks
            for cb in self._tick_callbacks:
                try:
                    cb(sym, self.SYMBOLDICT[key])
                except Exception as e:
                    logger.error(f"MockBrokerClient: Callback error: {e}")
            
            # Control pace - 50ms per candle
            time.sleep(0.05)
        
        logger.info(f"MockBrokerClient: Replay complete. Sent {len(all_candles)} ticks.")
    
    def prime_candles(self, symbols: List[Any], lookback_mins: int = 120):
        """
        Load historical candle data into SYMBOLDICT.
        This mimics the broker's prime_candles but uses recorded data.
        Uses flexible matching - matches by symbol name regardless of token.
        """
        logger.debug(f"MockBrokerClient: Priming {len(symbols)} symbols...")
        
        matched_count = 0
        
        # Build a mapping from symbol name to data
        symbol_to_data = {}
        for key, info in self._candle_data.items():
            # Use key (e.g., "NSE_NIFTY") as the symbol if not set
            data_symbol = info.get('symbol') or key
            # Extract short name (NSE_NIFTY -> NIFTY)
            short_name = data_symbol.split('_')[-1] if '_' in data_symbol else data_symbol
            symbol_to_data[short_name.upper()] = (key, info)
            # Also map the full key
            symbol_to_data[data_symbol.upper()] = (key, info)
        
        for item in symbols:
            # Get symbol name (could be in various formats)
            symbol_name = item.get('symbol', '') if isinstance(item, dict) else str(item)
            token = item.get('token', '') if isinstance(item, dict) else str(item)
            exch = item.get('exchange', 'NSE') if isinstance(item, dict) else 'NSE'
            
            # Try to find matching data by symbol name
            lookup_key = symbol_name.upper()
            
            if lookup_key in symbol_to_data:
                key, info = symbol_to_data[lookup_key]
                data_token = info.get('token', token)
                candles = info.get('candles', [])[-lookback_mins:]
                sym = info.get('symbol', key)
                
                # Store with multiple keys for compatibility
                entry = {
                    'symbol': symbol_name,
                    't': symbol_name,
                    'token': data_token,
                    'exchange': exch,
                    'ltp': float(candles[-1]['intc']) if candles else 0,
                    'high': float(candles[-1].get('inth', 0)) if candles else 0,
                    'low': float(candles[-1].get('intl', 0)) if candles else 0,
                    'volume': int(candles[-1].get('intv', 0)) if candles else 0,
                    'candles': candles
                }
                
                self.SYMBOLDICT[f"{exch}|{data_token}"] = entry
                self.SYMBOLDICT[f"NSE|{data_token}"] = entry
                self.SYMBOLDICT[f"NFO|{data_token}"] = entry
                self.SYMBOLDICT[symbol_name] = entry
                self.SYMBOLDICT[key] = entry
                
                matched_count += 1
                logger.debug(f"MockBrokerClient: Primed {symbol_name} (token:{data_token}) with {len(candles)} candles")
        
        if matched_count == 0:
            logger.warning(f"MockBrokerClient: No symbols matched! Data has: {list(symbol_to_data.keys())}")
        
        logger.info(f"MockBrokerClient: Primed {matched_count}/{len(symbols)} symbols")
    
    def get_symbol(self, token, exchange='NSE'):
        """Get symbol for token"""
        key = f"{exchange}|{token}"
        if key in self._candle_data:
            return self._candle_data[key].get('symbol', key)
        return key
    
    def get_company_name(self, token, exchange='NSE'):
        """Get company name for token"""
        return self.get_symbol(token, exchange)
    
    def get_token(self, symbol):
        """Get token for symbol"""
        for key, info in self._candle_data.items():
            if symbol.upper() in info.get('symbol', '').upper():
                return info.get('token', symbol)
        return symbol
    
    def get_ltp(self, key):
        """Get last traded price"""
        return self.SYMBOLDICT.get(key, {}).get('ltp', 0)
    
    def get_dk_levels(self, key):
        """Get dk levels"""
        d = self.SYMBOLDICT.get(key, {})
        return {'ltp': d.get('ltp', 0), 'high': d.get('high', 0), 'low': d.get('low', 0)}
    
    @property
    def TOKEN_TO_SYMBOL(self):
        """Provide dict-like access for compatibility"""
        return {v.get('token'): v.get('symbol') for v in self._candle_data.values()}
    
    @property
    def SYMBOL_TO_TOKEN(self):
        """Provide dict-like access for compatibility"""
        return {v.get('symbol'): v.get('token') for v in self._candle_data.values()}
    
    @property
    def TOKEN_TO_COMPANY(self):
        """Provide dict-like access for compatibility"""
        return {v.get('token'): v.get('symbol') for v in self._candle_data.values()}
    
    @property
    def TOKEN_TO_LOTSIZE(self):
        """Provide dict-like access for compatibility"""
        return {}
    
    @property
    def DERIVATIVE_OPTIONS(self):
        """Provide dict-like access for compatibility"""
        return []
    
    @property
    def DERIVATIVE_LOADED(self):
        """Provide dict-like access for compatibility"""
        return True
    
    @property
    def span_cache(self):
        return {}
    
    def login(self, factor2_override=None):
        """Mock login always succeeds"""
        logger.info("MockBrokerClient: Login successful (mock)")
        return True
    
    def close(self):
        """Close mock connection"""
        self._replaying = False
        logger.info("MockBrokerClient: Connection closed")
    
    def get_limits(self):
        """Return mock limits"""
        return {
            'liquid_cash': 1000000,
            'collateral_value': 0,
            'margin_used': 0,
            'total_power': 1000000,
            'available': 1000000,
            'payin': 0
        }
    
    def get_positions(self):
        """Return empty positions"""
        return []
    
    def get_order_history(self):
        """Return empty order history"""
        return []
    
    def place_put_credit_spread(self, **kwargs):
        """Mock - return success without placing"""
        logger.info(f"MockBrokerClient: place_put_credit_spread (mock, no actual order)")
        return {'ok': True, 'mock': True}
    
    def place_call_credit_spread(self, **kwargs):
        """Mock - return success without placing"""
        logger.info(f"MockBrokerClient: place_call_credit_spread (mock, no actual order)")
        return {'ok': True, 'mock': True}
    
    def place_future_order(self, **kwargs):
        """Mock - return success without placing"""
        logger.info(f"MockBrokerClient: place_future_order (mock, no actual order)")
        return {'ok': True, 'mock': True}
    
    def get_option_theta(self, symbol: str, expiry_date: str, strike_price: float, option_type: str) -> Optional[float]:
        """Mock theta return"""
        return -0.5
    
    def get_near_future(self, symbol, exchange='NFO'):
        """Mock near future"""
        return {'token': 'mock_token', 'tsym': symbol}
    
    def get_credit_spread_contracts(self, symbol, ltp, side, hedge_steps=4, expiry_type="monthly", instrument="OPTSTK"):
        """Mock credit spread contracts"""
        return {'ok': False, 'reason': 'mock_mode'}
    
    def calculate_span_for_spread(self, spread, product_type="I", haircut=0.20):
        """Mock span calculation"""
        return 0
    
    def calculate_future_margin(self, future_details, product_type="I", haircut=0.20):
        """Mock margin calculation"""
        return 0
    
    def get_option_ltp_by_symbol(self, tsym):
        """Mock option LTP"""
        return 0
    
    def load_nfo_futures_map(self):
        """No-op for mock"""
        pass
    
    def set_span_cache_path(self, path):
        """No-op for mock"""
        pass
    
    def load_span_cache(self):
        """No-op for mock"""
        pass
    
    def save_span_cache(self):
        """No-op for mock"""
        pass
    
    @property
    def api(self):
        """Return a mock API object"""
        return MockApi()
    
    @property
    def exchange_config(self):
        """Return empty exchange config"""
        return {}


class MockApi:
    """Mock API object for compatibility"""
    
    def get_time_price_series(self, exchange, token, starttime, endtime, interval):
        """Return empty - data comes from SYMBOLDICT"""
        return []
    
    def get_quotes(self, exchange, token):
        """Return mock quote"""
        return {'lp': 0, 'ltp': 0}
    
    def option_greek(self, **kwargs):
        """Return mock greek"""
        return {'stat': 'Ok', 'theta': '-0.5'}
    
    def get_limits(self):
        """Return mock limits"""
        return {'stat': 'Ok', 'cash': '1000000', 'collateral': '0', 'marginused': '0'}
    
    def get_positions(self):
        """Return empty positions"""
        return []
    
    def get_order_book(self):
        """Return empty order book"""
        return []


class MockResolver:
    """Mock resolver for contract lookups"""
    
    def __init__(self):
        pass
    
    def get_near_future(self, symbol, exchange, api):
        return {'token': 'mock_token', 'tsym': symbol}
    
    def get_credit_spread_contracts(self, symbol, ltp, side, hedge_steps, expiry_type, instrument):
        return {'ok': False, 'reason': 'mock_mode'}
    
    def resolve_option_symbol(self, *args, **kwargs):
        return {'ok': False, 'reason': 'mock_mode'}
    
    def resolve_futures_symbol(self, *args, **kwargs):
        return {'token': 'mock_token', 'tsym': 'mock'}
    
    def get_option_contracts(self, *args, **kwargs):
        return []


class MockMaster:
    """Mock scrip master for token lookups"""
    
    def __init__(self):
        self.TOKEN_TO_SYMBOL = {}
        self.SYMBOL_TO_TOKEN = {}
        self.TOKEN_TO_COMPANY = {}
        self.TOKEN_TO_LOTSIZE = {}
        self.DERIVATIVE_OPTIONS = []
        self.DERIVATIVE_LOADED = True
    
    def load_mappings(self, segment_name):
        pass
