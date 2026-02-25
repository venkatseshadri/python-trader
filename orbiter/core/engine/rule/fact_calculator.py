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
        facts = {}
        close_data = standardized_data.get('close')
        token = kwargs.get('token', 'UNKNOWN')
        data_len = len(close_data) if close_data is not None else 0
        
        logger.info(f"🧮 Calculating Tech Facts for {token} | Bars: {data_len}")

        if close_data is None or len(close_data) < 20:
            return facts

        # ⚡️ Optimize: Calculate indicators ONCE per tick
        indicators = self.analyzer.analyze(standardized_data)
        logger.trace(f"Indicators calculated: {list(indicators.keys())}")
        
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
                        # Expand other keys as sub-facts (e.g. market.orb.high)
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
        if not logged_in and app.engine and hasattr(app.engine.state, 'client'):
            api = app.engine.state.client.api
            logged_in = getattr(api, '_NorenApi__susertoken', None) is not None
            
        return { 
            "app.initialized": app.initialized,
            "app.logged_in": logged_in,
            "app.primed": app.primed
        }
