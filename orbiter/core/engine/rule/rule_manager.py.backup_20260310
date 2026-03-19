import logging
import traceback
import rule_engine
import re
import threading
from typing import List, Dict, Any, Callable, Optional
from orbiter.utils.data_manager import DataManager
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager
from .fact_calculator import FactCalculator
from .fact_converter import FactConverter
from orbiter.core.engine.session.session_manager import SessionManager
from orbiter.utils.utils import merge_dicts, safe_float

logger = logging.getLogger("ORBITER")

class RuleManager:
    def __init__(self, project_root: str, rules_file_path: str, session_manager: SessionManager):
        self.project_root = project_root
        self.rules_file_path = rules_file_path
        self.session_manager = session_manager
        self.constants = ConstantsManager.get_instance()
        self.schema_manager = SchemaManager.get_instance(project_root)
        self.rule_schema = self.schema_manager.get_key('rule_schema')
        
        fact_defs_path = DataManager.get_manifest_path(project_root, 'mandatory_files', 'fact_definitions')
        self.fact_definitions = DataManager.load_json(fact_defs_path)

        self.fact_calc = FactCalculator(project_root, self.fact_definitions)
        self.fact_converter = FactConverter(project_root)
        self.fact_providers = []
        self.rule_sets = []
        self.scoring_rules = []
        
        # Cache for compiled math evaluators to avoid re-compilation in loops
        self._score_evaluators = {} 
        
        self.rule_sets = self._load_and_compile_rules()
        logger.trace(f"📋 Initialized with {len(self.rule_sets)} rule sets")
        self.scoring_rules = self._load_and_compile_scoring_rules()

    def register_provider(self, provider: Callable[[], Dict[str, Any]]):
        if provider: self.fact_providers.append(provider)

    def clear_providers(self):
        self.fact_providers = []

    def _get_common_facts(self, source: Any) -> Dict[str, Any]:
        facts = {}
        for provider in self.fact_providers:
            try:
                p_facts = provider()
                facts.update({k.replace('.', '_'): v for k, v in p_facts.items()})
            except Exception as e:
                logger.error(f"Fact provider error: {e}")

        params = self.session_manager.get_all_strategy_parameters()
        for k, v in params.items(): facts[f"strategy_{k}"] = v
        
        # Inject filter tuning (Recursive flattening)
        def _flatten_filter(group_data, prefix):
            for name, val in group_data.items():
                new_prefix = f"{prefix}_{name}"
                if isinstance(val, dict):
                    _flatten_filter(val, new_prefix)
                else:
                    facts[new_prefix] = val

        filter_config = self.session_manager.filters
        _flatten_filter(filter_config, "filters")

        return facts

    def evaluate(self, source: Any, context: str = "global", **extra_facts) -> List[dict]:
        logger.trace(f"📋 Rule Manager evaluate called with context: {context}")
        logger.trace(f"📋 Rule sets loaded: {len(self.rule_sets)}")
        # Log the symbol from extra_facts
        logger.trace(f"🔭 [RuleManager.evaluate] extra_facts symbol: {extra_facts.get('symbol')}")
        facts = self._get_common_facts(source)
        
        # Always add score-related facts from extra_facts (needed for strategy rules in any context)
        if 'strategy_sum_bi' in extra_facts:
            facts['strategy_sum_bi'] = extra_facts.get('strategy_sum_bi', 0)
            facts['strategy_sum_uni'] = extra_facts.get('strategy_sum_uni', 0)
            logger.trace(f"[RuleManager.evaluate] Added score facts: sum_bi={extra_facts.get('strategy_sum_bi')}, sum_uni={extra_facts.get('strategy_sum_uni')}")
        
        ins_ctx = self.constants.get('fact_contexts', 'instrument_context')

        if context == ins_ctx:
            # 🚀 Optimization: If technical facts are already in extra_facts, don't re-calculate
            if 'market_adx' in extra_facts:
                facts.update({k.replace('.', '_'): v for k, v in extra_facts.items() if not k.startswith('instrument.') and (k.startswith('market_') or k.startswith('filter_') or k.startswith('sl_') or k.startswith('tp_'))})
            else:
                token_raw = extra_facts.get('token')
                token = token_raw.get('token') if isinstance(token_raw, dict) else token_raw
                exch = extra_facts.get('instrument_exchange') or extra_facts.get('instrument.exchange') or 'NSE'
                logger.info(f"🔍 Token: {token} | Exchange: {exch}")
                
                # 🔄 For BSE stock options, use BFO index data for ADX calculation
                if exch == 'BSE':
                    index_token = '1165486'  # SENSEX on BFO
                    index_exchange = 'BFO'
                    index_lookup_key = f"BFO|{index_token}"
                    raw_data = source.state.client.SYMBOLDICT.get(index_lookup_key)
                    if raw_data:
                        exch = 'BFO'
                        token = index_token
                        logger.info(f"🔄 Using BFO SENSEX data for ADX on BSE instrument")
                    else:
                        lookup_key = f"{exch}|{token}"
                        raw_data = source.state.client.SYMBOLDICT.get(lookup_key)
                        if not raw_data:
                            raw_data = source.state.client.SYMBOLDICT.get(token, {})
                else:
                    lookup_key = f"{exch}|{token}"
                    raw_data = source.state.client.SYMBOLDICT.get(lookup_key)
                    if not raw_data:
                        raw_data = source.state.client.SYMBOLDICT.get(token, {})
                    
                    if not raw_data:
                        logger.warning(f"[{self.__class__.__name__}.evaluate] - No data found for lookup_key={lookup_key}, token={token}, exch={exch}. SYMBOLDICT sample keys: {list(source.state.client.SYMBOLDICT.keys())[:5]}")
                
                candles = raw_data.get('candles', [])
                standardized = self.fact_converter.convert_candle_data(candles)
                
                # Use raw_data_for_filter if provided
                raw_data_for_filter = extra_facts.get('raw_data_for_filter')
                if not raw_data_for_filter:
                    last_candle = candles[-1] if candles else {}
                    ltp = safe_float(raw_data.get('lp') or raw_data.get('ltp') or last_candle.get('intc', 0))
                    raw_data_for_filter = {'lp': ltp}

                tech_facts_flat = self.fact_calc.calculate_technical_facts(
                    standardized, 
                    filter_config=self.session_manager.filters, 
                    raw_data_for_filter=raw_data_for_filter,
                    **extra_facts
                )
                tech_facts_flat["instrument.symbol"] = raw_data.get('symbol', 'UNKNOWN')
                
                defaults = {'market_adx': 0.0, 'market_ema_fast': 0.0, 'market_ema_slow': 1.0, 'market_rsi': 50.0, 'market_supertrend_dir': 0, 'market_supertrend': 1}
                facts.update(defaults)
                for k, v in tech_facts_flat.items():
                    facts[k.replace('.', '_')] = v

        # Flatten extra_facts too
        for k, v in extra_facts.items():
            facts[k.replace('.', '_')] = v
        triggered_ops = []
        op_key = self.rule_schema.get('actions_key', 'order_operations')

        # DEBUG: Log rule evaluation with key facts
        logger.debug(f"📋 Rule eval: {len(self.rule_sets)} rule_sets, facts keys: {list(facts.keys())[:10]}...")
        
        # TRACE: Log key strategy facts for debugging
        logger.trace(f"🔍 KEY FACTS: is_trade_window={facts.get('session_is_trade_window')}, active_positions={facts.get('portfolio_active_positions')}, sum_bi={facts.get('strategy_sum_bi')}, sum_uni={facts.get('strategy_sum_uni')}, market_adx={facts.get('market_adx')}")
        logger.trace(f"🔍 ALL FACTS: {facts}")
        
        for rule_set in self.rule_sets:
            try:
                # DEBUG: Log the full facts dict for strategy rules
                if 'MCX' in rule_set.get('name', ''):
                    logger.trace(f"🔍 Rule '{rule_set.get('name')}' evaluation - facts keys: {list(facts.keys())}")
                    logger.trace(f"🔍 Rule '{rule_set.get('name')}' - strategy_sum_bi={facts.get('strategy_sum_bi')}, market_adx={facts.get('market_adx')}")
                match_result = rule_set['engine'].matches(facts)
                if match_result:
                    logger.info(f"✅ Rule matched: {rule_set['name']}")
                    # IMPORTANT: Deep copy actions to avoid mutating the original rule_set objects
                    import copy
                    for op in rule_set[op_key]:
                        triggered_ops.append(copy.deepcopy(op))  # Deep copy to handle nested dicts
                else:
                    # TRACE: Log why each rule didn't match
                    logger.trace(f"❌ Rule NOT matched: {rule_set['name']} | Facts: is_trade_window={facts.get('session_is_trade_window')}, active_positions={facts.get('portfolio_active_positions')}")
            except Exception as e:
                logger.error(f"⚠️ Eval Error in [{rule_set['name']}]: {e}")
        return triggered_ops

    def evaluate_score(self, source: Any, context: str = "global", **extra_facts) -> float:
        facts = self._get_common_facts(source)
        ins_ctx = self.constants.get('fact_contexts', 'instrument_context')

        if context == ins_ctx:
            # 🚀 Optimization: If technical facts are already in extra_facts, don't re-calculate
            if 'market_adx' in extra_facts:
                facts.update({k.replace('.', '_'): v for k, v in extra_facts.items() if not k.startswith('instrument.') and (k.startswith('market_') or k.startswith('filter_') or k.startswith('sl_') or k.startswith('tp_'))})
            else:
                token_raw = extra_facts.get('token')
                token = token_raw.get('token') if isinstance(token_raw, dict) else token_raw
                exch = extra_facts.get('instrument_exchange') or extra_facts.get('instrument.exchange') or 'NSE'
                lookup_key = f"{exch}|{token}"
                
                raw_data = source.state.client.SYMBOLDICT.get(lookup_key)
                if not raw_data:
                    raw_data = source.state.client.SYMBOLDICT.get(token, {})
                
                candles = raw_data.get('candles', [])
                
                standardized = self.fact_converter.convert_candle_data(candles)
                
                # Use raw_data_for_filter if provided
                raw_data_for_filter = extra_facts.get('raw_data_for_filter')
                if not raw_data_for_filter:
                    last_candle = candles[-1] if candles else {}
                    ltp = safe_float(raw_data.get('lp') or raw_data.get('ltp') or last_candle.get('intc', 0))
                    raw_data_for_filter = {'lp': ltp}

                tech_facts_flat = self.fact_calc.calculate_technical_facts(
                    standardized, 
                    filter_config=self.session_manager.filters, 
                    raw_data_for_filter=raw_data_for_filter,
                    **extra_facts
                )
                if not tech_facts_flat:
                    return 0.0

                tech_facts_flat["instrument.symbol"] = raw_data.get('symbol', 'UNKNOWN')
                
                defaults = {'market_adx': 0.0, 'market_ema_fast': 0.0, 'market_ema_slow': 1.0, 'market_rsi': 50.0, 'market_supertrend_dir': 0, 'market_supertrend': 1}
                facts.update(defaults)
                logger.trace(f"[evaluate_score] Added defaults, now adding tech_facts_flat: {list(tech_facts_flat.keys())}")
                # Flatten tech facts properly
                for k, v in tech_facts_flat.items():
                    facts[k.replace('.', '_')] = v
        
        # Flatten extra_facts too
        for k, v in extra_facts.items():
            facts[k.replace('.', '_')] = v

        # Add filter scoring weights to facts - support both old (combined_score) and new (bidirectional/unidirectional) formats
        scoring_config = self.session_manager.filters.get('scoring', {}) if self.session_manager.filters else {}
        
        # Handle new bidirectional/unidirectional format
        if 'bidirectional' in scoring_config:
            bi_config = scoring_config.get('bidirectional', {})
            for k, v in bi_config.items():
                if isinstance(v, dict):
                    # Handle nested thresholds
                    for k2, v2 in v.items():
                        facts[f'filters_scoring_bidirectional_{k}_{k2}'] = v2
                        facts[f'filters.scoring.bidirectional.{k}.{k2}'] = v2
                else:
                    facts[f'filters_scoring_bidirectional_{k}'] = v
                    facts[f'filters.scoring.bidirectional.{k}'] = v
        
        if 'unidirectional' in scoring_config:
            uni_config = scoring_config.get('unidirectional', {})
            for k, v in uni_config.items():
                if isinstance(v, dict):
                    for k2, v2 in v.items():
                        facts[f'filters_scoring_unidirectional_{k}_{k2}'] = v2
                        facts[f'filters.scoring.unidirectional.{k}.{k2}'] = v2
                else:
                    facts[f'filters_scoring_unidirectional_{k}'] = v
                    facts[f'filters.scoring.unidirectional.{k}'] = v
        
        # Legacy combined_score support (backward compatibility)
        combined_config = scoring_config.get('combined_score', {})
        for k, v in combined_config.items():
            facts[f'filters_scoring_combined_score_{k}'] = v
            facts[f'filters.scoring.combined_score.{k}'] = v

        logger.trace(f"[evaluate_score] Facts keys before scoring: {list(facts.keys())}")
        logger.trace(f"[evaluate_score] Bi facts: market_ema_fast={facts.get('market_ema_fast')}, market_ema_slow={facts.get('market_ema_slow')}, market_supertrend_dir={facts.get('market_supertrend_dir')}, market_adx={facts.get('market_adx')}")
        logger.trace(f"[evaluate_score] Bi weights: weight_ema_slope={facts.get('filters_scoring_bidirectional_weight_ema_slope')}, weight_supertrend={facts.get('filters_scoring_bidirectional_weight_supertrend')}")
        logger.trace(f"[evaluate_score] Uni weights: weight_adx={facts.get('filters_scoring_unidirectional_weight_adx')}")

        # Guard against division by zero in EMA slope calculation
        # When EMA values are 0 (no data), set them equal so slope = 0 (not false signal)
        ema_fast = facts.get('market_ema_fast', 0.0)
        ema_slow = facts.get('market_ema_slow', 0.0)
        if ema_slow == 0:
            # No EMA data - set both to same value to get 0 slope
            facts['market_ema_fast'] = ema_fast if ema_fast > 0 else 1.0
            facts['market_ema_slow'] = facts['market_ema_fast']

        scores = {'sum_bi': 0.0, 'sum_uni': 0.0}
        for score_rule in self.scoring_rules:
            logger.trace(f"[evaluate_score] Evaluating rule: {score_rule.get('name')}")
            try:
                matches = score_rule['engine'].matches(facts)
                logger.trace(f"[evaluate_score] Rule '{score_rule.get('name')}' matches: {matches}")
                if matches:
                    expr_str = score_rule.get('scoring_expression')
                    if expr_str:
                        if expr_str not in self._score_evaluators:
                            self._score_evaluators[expr_str] = rule_engine.Rule(expr_str)
                        
                        # 🔥 DEBUG: Log facts if scoring is expected
                        if 'filter_supertrend_direction_numeric' not in facts:
                            logger.trace(f"Scoring Debug - Expression: {expr_str} | Keys: {list(facts.keys())}")
                        
                        try:
                            result = self._score_evaluators[expr_str].evaluate(facts)
                            logger.trace(f"[evaluate_score] Rule '{score_rule.get('name')}' result: {result}")
                        except Exception as eval_e:
                            logger.error(f"Scoring Eval Error: {eval_e} | Expression: {expr_str}")
                            raise eval_e
                        
                        score_value = float(result) if result is not None else 0.0
                        rule_name = score_rule.get('name', '')
                        
                        # Map rule name to score type
                        if 'Bidirectional' in rule_name:
                            scores['sum_bi'] = score_value
                            logger.trace(f"[evaluate_score] Set sum_bi = {score_value}")
                        elif 'Unidirectional' in rule_name:
                            scores['sum_uni'] = score_value
                            logger.trace(f"[evaluate_score] Set sum_uni = {score_value}")
                        else:
                            # Legacy fallback
                            scores['sum_bi'] = max(scores['sum_bi'], score_value)
            except Exception as e:
                logger.error(f"⚠️ Scoring Error [{score_rule.get('name')}]: {e}")
        
        logger.trace(f"[evaluate_score] Final scores: sum_bi={scores['sum_bi']}, sum_uni={scores['sum_uni']}")
        
        # Return combined score for backward compatibility (sum_bi + sum_uni)
        # Also set facts for strategy rules to access
        facts['strategy_sum_bi'] = scores['sum_bi']
        facts['strategy_sum_uni'] = scores['sum_uni']
        facts['strategy_trend_score'] = scores['sum_bi']  # Legacy compatibility
        logger.trace(f"[evaluate_score] Set facts: strategy_sum_bi={scores['sum_bi']}, strategy_sum_uni={scores['sum_uni']}")
        
        # Return both total score and the individual scores dict
        return scores['sum_bi'] + scores['sum_uni'], scores

    def _load_and_compile_rules(self) -> List[Dict]:
        logger.debug(f"📋 Loading rules from: {self.rules_file_path}")
        rules = self._compile_rules(self.rule_schema.get('rules_key', 'strategies'), self.rule_sets)
        logger.debug(f"📋 Loaded {len(rules)} rules")
        return rules

    def _load_and_compile_scoring_rules(self) -> List[Dict]:
        return self._compile_rules(self.rule_schema.get('scoring_rules_key', 'scoring_rules'), self.scoring_rules)

    def _compile_rules(self, rule_list_key: str, target_list: List[Dict]) -> List[Dict]:
        try:
            data = DataManager.load_json(self.rules_file_path)
            if not data: return []
            compiled = []
            strategies_key = self.rule_schema.get('rules_key', 'strategies')
            signals_key = self.rule_schema.get('conditions_key', 'market_signals')
            ops_key = self.rule_schema.get('actions_key', 'order_operations')
            prio_key = self.rule_schema.get('priority_key', 'priority')
            score_expr_key = self.rule_schema.get('score_expression_key', 'scoring_expression')

            for s in data.get(rule_list_key, []):
                expr = s.get('expression') or self._convert_to_expression(s.get(signals_key, {}))
                rule_entry = {"name": s.get('name', 'Unnamed'), "engine": rule_engine.Rule(expr), prio_key: s.get(prio_key, 0)}
                if ops_key in s: rule_entry[ops_key] = s.get(ops_key, [])
                if score_expr_key in s:
                    raw_expr = s.get(score_expr_key)
                    # Recursively replace all dots with underscores in the scoring expression
                    processed_score_expr = raw_expr.replace('.', '_')
                    rule_entry['scoring_expression'] = processed_score_expr
                compiled.append(rule_entry)
            return sorted(compiled, key=lambda x: x[prio_key], reverse=True)
        except Exception as e:
            logger.error(f"❌ Load Error {rule_list_key}: {e}")
            return []

    def _convert_to_expression(self, node: dict) -> str:
        operators = {
            "equal": "==", "notEqual": "!=", 
            "greaterThan": ">", "lessThan": "<", 
            "greaterThanOrEqual": ">=", "lessThanOrEqual": "<=",
            "greater_than": ">", "less_than": "<", 
            "greater_or_equal": ">=", "less_or_equal": "<=",
            "in": "in"
        }
        if 'allOf' in node: return "(" + " and ".join([self._convert_to_expression(c) for c in node['allOf']]) + ")"
        if 'anyOf' in node: return "(" + " or ".join([self._convert_to_expression(c) for c in node['anyOf']]) + ")"
        f_key, o_key, v_key = self.rule_schema.get('fact_key', 'fact'), self.rule_schema.get('operator_key', 'operator'), self.rule_schema.get('value_key', 'value')
        if f_key in node:
            fact_name = node[f_key].replace('.', '_')
            val = node.get(v_key)
            if isinstance(val, bool): val = str(val).lower()
            elif isinstance(val, str): val = f"'{val}'"
            op = operators.get(node.get(o_key, 'equal'), '==')
            return f"{fact_name} {op} {val}"
        return "true"
