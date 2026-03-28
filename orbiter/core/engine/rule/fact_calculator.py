# orbiter/core/engine/rule/fact_calculator.py

import logging
import traceback
import talib
import numpy as np
import importlib
from typing import Dict, Any, List
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager
from .technical_analyzer import TechnicalAnalyzer

logger = logging.getLogger("ORBITER")

_yf_indicators_cache = {'value': None, 'timestamp': 0}

# MCX to Yahoo Finance commodity futures mapping
MCX_YF_SYMBOLS = {
    'CRUDEOILM': 'CL=F',
    'NATURALGAS': 'NG=F',
    'NATGASMINI': 'NG=F',
    'GOLDM': 'GC=F',
    'GOLDTEN': 'GC=F',
    'GOLDGUINEA': 'GC=F',
    'SILVERM': 'SI=F',
    'SILVERMIC': 'SI=F',
    'ALUMINI': 'ALI=F',
    'LEADMINI': 'PB=F',
    'ZINCMINI': 'ZN=F',
}

class FactCalculator:
    def __init__(self, project_root: str, fact_definitions: Dict[str, Any]):
        logger.trace(f"[FactCalculator.__init__] - Initializing with project_root: {project_root}")
        self.constants = ConstantsManager.get_instance()
        self.schema_manager = SchemaManager.get_instance(project_root)
        self.fact_schema = self.schema_manager.get_key('fact_definition_schema')
        self.fact_definitions = fact_definitions
        self._custom_modules = {}
        self.analyzer = TechnicalAnalyzer()

    def calculate_technical_facts(self, standardized_data: Dict[str, np.ndarray], filter_config: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        import time
        facts = {}
        close_data = standardized_data.get('close')
        token = kwargs.get('token', 'UNKNOWN')
        data_len = len(close_data) if close_data is not None else 0
        
        logger.info(f"🧮 Calculating Tech Facts for {token} | Bars: {data_len}")

        if close_data is None or len(close_data) < 12:
            exchange = kwargs.get('instrument_exchange', kwargs.get('instrument.exchange', ''))
            is_mcx = exchange.upper() == 'MCX'
            
            if is_mcx:
                # 🔄 MCX: Try YF fallback using commodity futures
                yf_symbol = MCX_YF_SYMBOLS.get(token.upper())
                
                if yf_symbol:
                    logger.warning(f"[{self.__class__.__name__}] - MCX instrument {token} has insufficient data ({data_len} bars). Trying YF fallback: {yf_symbol}")
                    global _yf_indicators_cache
                    current_time = time.time()
                    
                    # Create cache key for this specific commodity
                    cache_key = f'mcx_{token.upper()}'
                    if cache_key not in _yf_indicators_cache or (current_time - _yf_indicators_cache.get(f'{cache_key}_ts', 0)) > 300:
                        try:
                            import yfinance as yf
                            import talib as talib_lib
                            
                            ticker = yf.Ticker(yf_symbol)
                            df = ticker.history(period='1d', interval='5m')
                            
                            if df is not None and len(df) >= 14:
                                high = np.array(df['High'].values, dtype=float)
                                low = np.array(df['Low'].values, dtype=float)
                                close = np.array(df['Close'].values, dtype=float)
                                
                                adx = talib_lib.ADX(high, low, close, timeperiod=14)[-1]
                                ema_fast = talib_lib.EMA(close, timeperiod=5)[-1]
                                ema_slow = talib_lib.EMA(close, timeperiod=20)[-1]
                                atr = talib_lib.ATR(high, low, close, timeperiod=10)[-1]
                                
                                # SuperTrend direction
                                hl2 = (high + low) / 2
                                upper = hl2 + (3 * atr)
                                lower = hl2 - (3 * atr)
                                st_dir = 1 if close[-1] > lower[-1] else -1
                                
                                yf_data = {
                                    'adx': round(float(adx), 2) if not np.isnan(adx) else 0,
                                    'ema_fast': round(float(ema_fast), 2),
                                    'ema_slow': round(float(ema_slow), 2),
                                    'supertrend_dir': st_dir,
                                    'supertrend': round(float(atr * 3), 2),
                                }
                                
                                _yf_indicators_cache[cache_key] = yf_data
                                _yf_indicators_cache[f'{cache_key}_ts'] = current_time
                                logger.info(f"🔄 MCX YF fallback for {token}: ADX={yf_data['adx']}, EMA_fast={yf_data['ema_fast']}, ST_dir={yf_data['supertrend_dir']}")
                            else:
                                logger.warning(f"MCX YF fallback: No data for {yf_symbol}")
                        except Exception as e:
                            logger.warning(f"MCX YF fallback failed for {token}: {e}")
                    
                    # Apply cached YF values
                    if cache_key in _yf_indicators_cache:
                        yf = _yf_indicators_cache[cache_key]
                        facts['index.adx'] = facts['index_adx'] = yf.get('adx', 0)
                        facts['index.ema_fast'] = facts['index_ema_fast'] = yf.get('ema_fast', 0)
                        facts['index.ema_slow'] = facts['index_ema_slow'] = yf.get('ema_slow', 0)
                        facts['index.supertrend_dir'] = facts['index_supertrend_dir'] = yf.get('supertrend_dir', 0)
                        facts['index.supertrend'] = facts['index_supertrend'] = yf.get('supertrend', 0)
                        facts['data_source'] = 'yf_mcx_fallback'
                        logger.info(f"🔄 Applied MCX YF fallback: ADX={yf.get('adx')}")
                        return facts
                
                # No YF mapping or YF failed - return zeros
                logger.warning(f"[{self.__class__.__name__}] - MCX instrument {token} has no data ({data_len} bars) and no YF fallback. Returning zeros.")
                facts['index.adx'] = facts['index_adx'] = 0
                facts['index.ema_fast'] = facts['index_ema_fast'] = 0.0
                facts['index.ema_slow'] = facts['index_ema_slow'] = 0.0
                facts['index.supertrend_dir'] = facts['index_supertrend_dir'] = 0
                facts['index.supertrend'] = facts['index_supertrend'] = 0
                facts['data_source'] = 'none'
                return facts
            
            logger.warning(f"[{self.__class__.__name__}] - Insufficient candle data for {token}: {data_len} bars (need >= 12). Using YF fallback.")
            # Select correct index based on exchange: NFO->NIFTY, BFO->SENSEX
            exchange = kwargs.get('instrument_exchange', kwargs.get('instrument.exchange', ''))
            if exchange.upper() == 'BFO':
                yf_index = 'SENSEX'
            else:
                yf_index = 'NIFTY'  # Default to NIFTY for NFO/NSE
            
            logger.info(f"🔄 Using YF {yf_index} for fallback (exchange={exchange})")
            # 🔄 Fallback: Use Yahoo Finance for ALL indicators when broker candles are insufficient
            current_time = time.time()
            
            # Cache YF data for 5 minutes
            if _yf_indicators_cache['value'] is None or (current_time - _yf_indicators_cache['timestamp']) > 300:
                try:
                    from orbiter.utils.yf_adapter import get_all_indicators
                    yf_data = get_all_indicators(yf_index, '5m')
                    if yf_data:
                        _yf_indicators_cache = {'value': yf_data, 'timestamp': current_time}
                        logger.info(f"🔄 Using YF indicators fallback: {yf_data}")
                    else:
                        logger.warning("YF fallback returned no data")
                except Exception as e:
                    logger.warning(f"YF indicators fallback failed: {e}")
            
            # Apply YF fallback values
            if _yf_indicators_cache.get('value'):
                yf = _yf_indicators_cache['value']
                facts['index.adx'] = facts['index_adx'] = yf.get('adx', 0)
                facts['index.ema_fast'] = facts['index_ema_fast'] = yf.get('ema_fast', 0)
                facts['index.ema_slow'] = facts['index_ema_slow'] = yf.get('ema_slow', 0)
                facts['index.supertrend_dir'] = facts['index_supertrend_dir'] = yf.get('supertrend_dir', 0)
                facts['index.supertrend'] = facts['index_supertrend'] = yf.get('supertrend', 0)
                facts['data_source'] = 'yf_fallback'
                logger.info(f"🔄 Applied YF fallback: ADX={yf.get('adx')}, EMA_fast={yf.get('ema_fast')}, ST_dir={yf.get('supertrend_dir')}")
            else:
                # No YF data - use zeros
                facts['index.adx'] = facts['index_adx'] = 0
                facts['index.ema_fast'] = facts['index_ema_fast'] = 0.0
                facts['index.ema_slow'] = facts['index_ema_slow'] = 0.0
                facts['index.supertrend_dir'] = facts['index_supertrend_dir'] = 0
                facts['index.supertrend'] = facts['index_supertrend'] = 0
                facts['data_source'] = 'none'
            
            return facts

        # ⚡️ Optimize: Calculate indicators ONCE per tick
        logger.trace(f"[fact_calculator.calculate_technical_facts] standardized_data keys: {list(standardized_data.keys())}")
        logger.trace(f"[fact_calculator.calculate_technical_facts] close array: {standardized_data.get('close', 'NOT FOUND')[:5] if 'close' in standardized_data else 'NOT FOUND'}")
        logger.trace(f"[fact_calculator.calculate_technical_facts] high array: {standardized_data.get('high', 'NOT FOUND')[:5] if 'high' in standardized_data else 'NOT FOUND'}")
        logger.trace(f"[fact_calculator.calculate_technical_facts] low array: {standardized_data.get('low', 'NOT FOUND')[:5] if 'low' in standardized_data else 'NOT FOUND'}")
        
        indicators = self.analyzer.analyze(standardized_data)
        logger.trace(f"Indicators calculated: {list(indicators.keys())}")
        
        # Check if ADX is 0/NaN - try YF fallback for MCX
        adx_value = indicators.get('market_adx', 0)
        logger.trace(f"[fact_calculator] adx_value={adx_value}, type={type(adx_value)}, is_nan={np.isnan(adx_value) if isinstance(adx_value, float) else 'not_float'}")
        exchange = kwargs.get('instrument_exchange', kwargs.get('instrument.exchange', ''))
        symbol = kwargs.get('instrument_symbol', kwargs.get('instrument.symbol', token))  # Use symbol name for YF lookup
        logger.trace(f"[fact_calculator] exchange={exchange}, token={token}, symbol={symbol}")
        
        if (adx_value == 0 or adx_value is None or (isinstance(adx_value, float) and np.isnan(adx_value))) and exchange.upper() == 'MCX':
            yf_symbol = MCX_YF_SYMBOLS.get(symbol.upper() if isinstance(symbol, str) else token.upper())
            if yf_symbol:
                logger.warning(f"MCX ADX is {adx_value}, trying YF fallback for {token} ({yf_symbol})")
                try:
                    import yfinance as yf
                    import talib as talib_lib
                    ticker = yf.Ticker(yf_symbol)
                    df = ticker.history(period='1d', interval='5m')
                    
                    if df is not None and len(df) >= 14:
                        high = np.array(df['High'].values, dtype=float)
                        low = np.array(df['Low'].values, dtype=float)
                        close = np.array(df['Close'].values, dtype=float)
                        
                        adx = talib_lib.ADX(high, low, close, timeperiod=14)[-1]
                        ema_fast = talib_lib.EMA(close, timeperiod=5)[-1]
                        ema_slow = talib_lib.EMA(close, timeperiod=20)[-1]
                        atr = talib_lib.ATR(high, low, close, timeperiod=10)[-1]
                        
                        hl2 = (high + low) / 2
                        upper = hl2 + (3 * atr)
                        lower = hl2 - (3 * atr)
                        st_dir = 1 if close[-1] > lower[-1] else -1
                        
                        indicators['index_adx'] = indicators['index.adx'] = round(float(adx), 2) if not np.isnan(adx) else 0
                        indicators['index_ema_fast'] = indicators['index.ema_fast'] = round(float(ema_fast), 2)
                        indicators['index_ema_slow'] = indicators['index.ema_slow'] = round(float(ema_slow), 2)
                        indicators['index_supertrend_dir'] = indicators['index.supertrend_dir'] = st_dir
                        indicators['index_supertrend'] = indicators['index.supertrend'] = round(float(atr * 3), 2)
                        
                        logger.info(f"🔄 MCX YF fallback applied: ADX={indicators['index_adx']}, ST_dir={st_dir}")
                except Exception as e:
                    logger.warning(f"MCX YF fallback failed: {e}")
        
        # Add indicators as index.* facts (BOTH dot and underscore formats)
        # Indicators from TechnicalAnalyzer already have full key names like 'market_supertrend_dir'
        for k, v in indicators.items():
            facts[k] = v  # Use key as-is
        
        facts['data_source'] = 'broker'
        
        input_map = {k: v for k, v in standardized_data.items() if isinstance(v, np.ndarray)}
        
        f_key = self.fact_schema.get('facts_key')
        p_key = self.fact_schema.get('provider_key')
        m_key = self.fact_schema.get('method_key')
        param_key = self.fact_schema.get('params_key')
        in_key = self.fact_schema.get('inputs_key')

        # Flatten strategy filters for easy lookup (Recursive)
        flat_filters = {}
        def _flatten(d):
            for k, v in d.items():
                if isinstance(v, dict):
                    if 'enabled' in v: # Leaf node (filter config)
                        flat_filters[k] = v
                    else: # Structural node (group)
                        _flatten(v)
        
        if filter_config:
            _flatten(filter_config)

        for name, definition in self.fact_definitions.get(f_key, {}).items():
            f_id = name.split('.')[-1]
            strat_settings = flat_filters.get(f_id, {"enabled": True})
            
            if not strat_settings.get('enabled', True):
                continue

            # 🅰️ TA-Lib Provider
            if definition[p_key] == 'talib':
                try:
                    method = getattr(talib, definition[m_key])
                    inputs = [input_map[inp] for inp in definition[in_key]]
                    params = definition[param_key].copy()
                    
                    if 'time_period' in strat_settings: params['timeperiod'] = strat_settings['time_period']
                    for k, v in strat_settings.items():
                        if k in params: params[k] = v

                    result = method(*inputs, **params)
                    facts[name] = round(float(result[-1]), 2) if not np.isnan(result[-1]) else 0.0
                except Exception as e:
                    logger.warning(f"Failed to calculate {name}: {e}")
                    facts[name] = 0.0

            # 🅱️ Custom Filter Provider (F1-F11)
            elif definition[p_key] == 'custom':
                try:
                    module_path = definition.get('module')
                    method_name = definition.get('method')
                    
                    if module_path not in self._custom_modules:
                        self._custom_modules[module_path] = importlib.import_module(module_path)
                    
                    method = getattr(self._custom_modules[module_path], method_name, None)
                    
                    # 🚀 Fix: Handle class-based filters (like DynamicBudgetTP)
                    if method is None:
                        # Try to find a class in the module that has the method
                        for attr_name in dir(self._custom_modules[module_path]):
                            attr = getattr(self._custom_modules[module_path], attr_name)
                            if isinstance(attr, type) and hasattr(attr, method_name):
                                # Instantiate and get method
                                logger.trace(f"[FactCalculator] - Instantiating class {attr_name} for filter {name}")
                                instance = attr()
                                method = getattr(instance, method_name)
                                break
                    
                    if method is None:
                        raise AttributeError(f"Module {module_path} has no attribute {method_name}")

                    # Custom filters expect (raw_data, candles, **kwargs)
                    # raw_data should contain lp, o, h, l, c for filters to work
                    raw_data_for_filter = kwargs.get('raw_data_for_filter', {})
                    raw_candles = standardized_data.get('_raw_list', [])
                    
                    # 🔥 Inject VERBOSE_LOGS for filters, merge kwargs carefully
                    filter_kwargs = {
                        **definition.get(param_key, {}), 
                        **strat_settings,
                        'indicators': indicators,
                        'VERBOSE_LOGS': logger.isEnabledFor(logging.DEBUG)
                    }
                    
                    # Merge incoming kwargs but skip those already explicitly handled or from definition
                    for k, v in kwargs.items():
                        if k not in filter_kwargs and k != 'raw_data_for_filter':
                            filter_kwargs[k] = v
                    
                    logger.trace(f"[FactCalculator] - Calling custom filter {name} with {len(raw_candles)} candles.")
                    
                    res = method(raw_data_for_filter, raw_candles, **filter_kwargs)
                    
                    if isinstance(res, dict):
                        facts[name] = res.get('score', 0.0)
                        # Expand other keys as sub-facts (e.g. index.orb.high)
                        for k, v in res.items():
                            if k != 'score': facts[f"{name}.{k}"] = v
                    else:
                        facts[name] = float(res)
                except Exception as e:
                    logger.warning(f"Custom filter {name} failed: {e}")
                    facts[name] = 0.0
                    
        return facts

    def calculate_portfolio_facts(self, state: Any) -> Dict[str, Any]:
        realized = getattr(state, 'realized_pnl', 0.0)
        return {
            "portfolio.total_pnl": realized,
            "portfolio.active_positions": len(state.active_positions)
        }

    def calculate_app_facts(self, app: Any) -> Dict[str, Any]:
        logged_in = bool(getattr(app, 'logged_in', False))
        if not logged_in and app.ctx.engine and hasattr(app.ctx.engine.state, 'client'):
            api = app.ctx.engine.state.client.api
            logged_in = getattr(api, '_NorenApi__susertoken', None) is not None
        
        primed = app.ctx.engine.state.primed if app.ctx and app.ctx.engine and app.ctx.engine.state else False
        
        return { 
            "app.initialized": app.initialized,
            "app.logged_in": logged_in,
            "app.primed": primed
        }
