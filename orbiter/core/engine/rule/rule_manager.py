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
                
                defaults = {'market_adx': 0.0, 'market_ema_fast': 0.0, 'market_ema_slow': 0.0, 'market_rsi': 50.0, 'market_supertrend_dir': 0}
                facts.update(defaults)
                for k, v in tech_facts_flat.items():
                    facts[k.replace('.', '_')] = v

        # Flatten extra_facts too
        for k, v in extra_facts.items():
            facts[k.replace('.', '_')] = v
        triggered_ops = []
        op_key = self.rule_schema.get('actions_key', 'order_operations')

        for rule_set in self.rule_sets:
            try:
                if rule_set['engine'].matches(facts):
                    triggered_ops.extend(rule_set[op_key])
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
                
                defaults = {'market_adx': 0.0, 'market_ema_fast': 0.0, 'market_ema_slow': 0.0, 'market_rsi': 50.0, 'market_supertrend_dir': 0}
                facts.update(defaults)
                # Flatten tech facts properly
                for k, v in tech_facts_flat.items():
                    facts[k.replace('.', '_')] = v
        
        # Flatten extra_facts too
        for k, v in extra_facts.items():
            facts[k.replace('.', '_')] = v

        max_score = 0.0
        for score_rule in self.scoring_rules:
            try:
                if score_rule['engine'].matches(facts):
                    expr_str = score_rule.get('scoring_expression')
                    if expr_str:
                        if expr_str not in self._score_evaluators:
                            self._score_evaluators[expr_str] = rule_engine.Rule(expr_str)
                        
                        # 🔥 DEBUG: Log facts if scoring is expected
                        if 'filter_supertrend_direction_numeric' not in facts:
                            logger.trace(f"Scoring Debug - Expression: {expr_str} | Keys: {list(facts.keys())}")
                        
                        try:
                            result = self._score_evaluators[expr_str].evaluate(facts)
                        except Exception as eval_e:
                            logger.error(f"Scoring Eval Error: {eval_e} | Expression: {expr_str}")
                            raise eval_e
                        max_score = max(max_score, float(result) if result is not None else 0.0)
            except Exception as e:
                logger.error(f"⚠️ Scoring Error [{score_rule['name']}]: {e}")
        return max_score

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
        operators = {"equal": "==", "notEqual": "!=", "greaterThan": ">", "lessThan": "<", "greaterThanOrEqual": ">=", "lessThanOrEqual": "<=", "in": "in"}
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
