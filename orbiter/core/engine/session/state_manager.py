from datetime import datetime
import os
import json
import logging
import traceback # Import traceback
from typing import Dict, Any, List, Optional
from orbiter.utils.data_manager import DataManager
from orbiter.utils.json_helpers import JSONEncoder
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.meta_config_manager import MetaConfigManager
import rule_engine

logger = logging.getLogger("ORBITER")

class StateManager:
    def __init__(self, client, symbols: List[str], config: Dict[str, Any], segment_name: str = 'nfo'):
        logger.debug(f"[{self.__class__.__name__}.__init__] - Initializing StateManager for segment: {segment_name}")
        self.client = client
        self.symbols = symbols
        self.config = config
        self.segment_name = segment_name.lower()
        project_root = getattr(self.client, 'project_root', None)
        if project_root is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.constants = ConstantsManager.get_instance(project_root)
        self.meta_config = MetaConfigManager.get_instance(project_root)
        self.ghost_template_schema = self.meta_config.get_key('ghost_template_file_schema')
        self.rule_file_schema = self.meta_config.get_key('rule_file_schema')

        self.active_positions = {}
        self.exit_history = {}
        self.opening_scores = {}
        
        self.max_portfolio_pnl = 0.0
        self.global_tsl_active = False
        self.realized_pnl = 0.0
        self.trade_count = 0

        self.last_scan_metrics = []
        self.last_scan_log_ts = 0
        self.filter_results_cache = {}
        
        self.evaluator = None
        self.executor = None
        self.syncer = None
        
        self.verbose_logs = self.config.get('verbose_logs', False)
        
        self.state_file = DataManager.get_manifest_path(project_root, 'settings', 'session_state_file')
        self.client.set_span_cache_path(DataManager.get_manifest_path(project_root, 'settings', 'span_cache_file'))
        self.client.load_span_cache()
        logger.debug(f"[{self.__class__.__name__}.__init__] - State file: {self.state_file}, Span cache: {self.client.span_cache_path}")

        ghost_template_path = DataManager.get_manifest_path(project_root, 'mandatory_files', 'ghost_position_template')
        self.ghost_template = DataManager.load_json(ghost_template_path)
        
        strategy_derivation_key = self.ghost_template_schema.get('strategy_derivation_key', 'strategy_derivation')
        self.ghost_strategy_rules = self._compile_ghost_strategy_rules(self.ghost_template.get(strategy_derivation_key, []))
        logger.debug(f"[{self.__class__.__name__}.__init__] - Loaded ghost position template from {ghost_template_path}. Compiled {len(self.ghost_strategy_rules)} strategy derivation rules.")


    def _compile_ghost_strategy_rules(self, rules_data: List[Dict]) -> List[Dict]:
        logger.debug(f"[{self.__class__.__name__}._compile_ghost_strategy_rules] - Compiling {len(rules_data)} ghost strategy rules.")
        compiled_rules = []
        conditions_key = self.ghost_template_schema.get('conditions_key', 'conditions')
        actions_key = self.ghost_template_schema.get('actions_key', 'actions')
        
        for rule_data in rules_data:
            conditions_expr = self._convert_to_expression(rule_data.get(conditions_key, {}))
            compiled_rules.append({
                "name": rule_data.get('name', 'Unnamed Ghost Rule'),
                "engine": rule_engine.Rule(conditions_expr),
                actions_key: rule_data.get(actions_key, [])
            })
            logger.trace(f"[{self.__class__.__name__}._compile_ghost_strategy_rules] - Compiled rule '{rule_data.get('name', 'Unnamed Ghost Rule')}': {conditions_expr}")
        return compiled_rules
        
    def _convert_to_expression(self, conditions: dict) -> str:
        parts = []
        operators = {"equal": "==", "notEqual": "!=", "greaterThan": ">", "lessThan": "<", "greaterThanOrEqual": ">=", "lessThanOrEqual": "<=", "in": "in"}
        
        fact_key = self.rule_file_schema.get('fact_key', 'fact')
        operator_key = self.rule_file_schema.get('operator_key', 'operator')
        value_key = self.rule_file_schema.get('value_key', 'value')

        all_of_key = self.meta_config.get_key('rule_file_schema', 'all_of_key', 'allOf')
        all_of = conditions.get(all_of_key, [])
        if not all_of and fact_key in conditions: all_of = [conditions]
        for c in all_of:
            val = f"'{c[value_key]}'" if isinstance(c[value_key], str) else c[value_key]
            parts.append(f"{c[fact_key]} {operators.get(c[operator_key], '==')} {val}")
        return " and ".join(parts) if parts else "true"


    def save_session(self):
        """Persist active positions and exit history to disk"""
        logger.debug(f"[{self.__class__.__name__}.save_session] - Attempting to save session state to {self.state_file}")
        try:
            sanitized_positions = {}
            for token, info in self.active_positions.items():
                pos_copy = info.copy()
                if 'config' in pos_copy: del pos_copy['config']
                sanitized_positions[token] = pos_copy

            data = {
                'last_updated': datetime.now().timestamp(),
                'active_positions': sanitized_positions,
                'exit_history': self.exit_history,
                'opening_scores': self.opening_scores,
                'max_portfolio_pnl': self.max_portfolio_pnl,
                'global_tsl_active': self.global_tsl_active,
                'realized_pnl': self.realized_pnl,
                'trade_count': self.trade_count
            }
            
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            tmp_file = self.state_file + ".tmp"
            with open(tmp_file, 'w') as f:
                json.dump(data, f, indent=4, cls=JSONEncoder)
            os.replace(tmp_file, self.state_file)
            logger.info(f"[{self.__class__.__name__}.save_session] - Session state saved successfully.")
                
        except Exception as e:
            msg_tpl = self.constants.get('magic_strings', 'save_session_fail_msg', "⚠️ Failed to save session: {error}")
            logger.error(msg_tpl.format(error=e))
            logger.debug(f"[{self.__class__.__name__}.save_session] - Full traceback: {traceback.format_exc()}")


    def load_session(self):
        """Recover session from disk or Cloud Snapshot (Google Sheets)"""
        logger.debug(f"[{self.__class__.__name__}.load_session] - Attempting to load session state from {self.state_file}")
        data = None
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                
                freshness_minutes = self.config.get('session_freshness_minutes', self.constants.get('magic_strings', 'default_session_freshness_minutes', 30))
                if (datetime.now().timestamp() - data.get('last_updated', 0)) > (freshness_minutes * 60):
                    logger.warning(self.constants.get('magic_strings', 'session_stale_msg').format(minutes=freshness_minutes))
                    data = None
            except Exception as e:
                msg_tpl = self.constants.get('magic_strings', 'local_load_fail_msg', "⚠️ Local load failed: {error}")
                logger.error(msg_tpl.format(error=e))
                logger.debug(f"[{self.__class__.__name__}.load_session] - Full traceback for local load failure: {traceback.format_exc()}")

        if not data:
            logger.debug(f"[{self.__class__.__name__}.load_session] - No valid local session data found or it was stale.")
            return

        try:
            raw_positions = data.get('active_positions', {})
            for token, info in raw_positions.items():
                if 'entry_time' in info:
                    info['entry_time'] = datetime.fromisoformat(info['entry_time'])
                self.active_positions[token] = info
            
            self.exit_history = data.get('exit_history', {})
            self.opening_scores = data.get('opening_scores', {})
            self.max_portfolio_pnl = data.get('max_portfolio_pnl', 0.0)
            self.global_tsl_active = False
            self.realized_pnl = data.get('realized_pnl', 0.0)
            self.trade_count = data.get('trade_count', 0)
            
            if self.active_positions:
                logger.info(self.constants.get('magic_strings', 'pos_recovered_msg').format(count=len(self.active_positions), source='Cloud' if not os.path.exists(self.state_file) else 'Disk'))
            logger.debug(f"[{self.__class__.__name__}.load_session] - Session state loaded and re-hydrated.")
        except Exception as e:
            msg_tpl = self.constants.get('magic_strings', 'rehydrate_fail_msg', "⚠️ Failed to re-hydrate session: {error}")
            logger.error(msg_tpl.format(error=e))
            logger.debug(f"[{self.__class__.__name__}.load_session] - Full traceback for re-hydration failure: {traceback.format_exc()}")


    def sync_with_broker(self):
        """
        Queries the broker for actual open positions and matches them with our state.
        Missing positions are re-imported with configurable defaults from a template.
        """
        logger.debug(f"[{self.__class__.__name__}.sync_with_broker] - Starting broker synchronization.")
        real_positions = self.client.get_positions()
        if not real_positions:
            logger.info(self.constants.get('magic_strings', 'broker_zero_pos_msg'))
            return

        for p in real_positions:
            qty = int(p.get('netqty', 0))
            if qty == 0: continue
            
            token = f"{p['exch']}|{p['token']}"
            if token not in self.active_positions:
                logger.warning(self.constants.get('magic_strings', 'ghost_pos_msg').format(symbol=p['tsym'], qty=abs(qty)))
                
                default_template_key = self.ghost_template_schema.get('default_template_key', 'default_ghost_position_template')
                ghost_pos = self.ghost_template.get(default_template_key, {}).copy()

                ghost_pos["entry_price"] = float(p.get('avgprc', 0))
                ghost_pos["entry_time"] = datetime.now()
                ghost_pos["symbol"] = p['tsym']
                ghost_pos["company_name"] = self.client.get_company_name(p['token'], exchange=p['exch'])
                ghost_pos["lot_size"] = abs(qty)
                ghost_pos["pnl_rs"] = float(p.get('rpnl', 0)) + float(p.get('urpnl', 0))

                derived_strategy = self._derive_ghost_strategy(p, qty)
                ghost_pos["strategy"] = derived_strategy if derived_strategy else ghost_pos.get("strategy", self.constants.get('magic_strings', 'unknown_strategy_name', "UNKNOWN"))
                
                self.active_positions[token] = ghost_pos
                logger.debug(f"[{self.__class__.__name__}.sync_with_broker] - Re-imported ghost position: {ghost_pos}")
        
        logger.info(self.constants.get('magic_strings', 'handover_complete_msg').format(count=len(self.active_positions)))

    def _derive_ghost_strategy(self, broker_pos: Dict[str, Any], qty: int) -> Optional[str]:
        """
        Applies rules from ghost_position_template to derive the strategy for a ghost position.
        """
        logger.trace(f"[{self.__class__.__name__}._derive_ghost_strategy] - Deriving strategy for broker_pos: {broker_pos.get('tsym')}, qty: {qty}")
        facts = {f"p.{k.lower()}": v for k, v in broker_pos.items()}
        facts["p.qty_positive"] = qty > 0
        facts["p.qty_negative"] = qty < 0

        strategy_derivation_key = self.ghost_template_schema.get('strategy_derivation_key', 'strategy_derivation')
        conditions_key = self.ghost_template_schema.get('conditions_key', 'conditions')
        actions_key = self.ghost_template_schema.get('actions_key', 'actions')
        set_field_key = self.ghost_template_schema.get('set_field_key', 'set_field')
        value_if_qty_positive_key = self.ghost_template_schema.get('value_if_qty_positive_key', 'value_if_qty_positive')
        value_if_qty_negative_key = self.ghost_template_schema.get('value_if_qty_negative_key', 'value_if_qty_negative')


        for rule_set in self.ghost_strategy_rules:
            logger.trace(f"[{self.__class__.__name__}._derive_ghost_strategy] - Checking ghost strategy rule: {rule_set.get('name')}")
            try:
                if rule_set['engine'].matches(facts):
                    logger.debug(f"[{self.__class__.__name__}._derive_ghost_strategy] - Ghost strategy rule '{rule_set.get('name')}' matched.")
                    for action in rule_set[actions_key]:
                        if action.get(set_field_key) == "strategy":
                            if facts["p.qty_positive"] and action.get(value_if_qty_positive_key):
                                return action[value_if_qty_positive_key]
                            if facts["p.qty_negative"] and action.get(value_if_qty_negative_key):
                                return action[value_if_qty_negative_key]
            except Exception as e:
                logger.error(f"[{self.__class__.__name__}._derive_ghost_strategy] - Error deriving ghost strategy for {broker_pos.get('tsym')}: {e}")
                import traceback
                logger.debug(f"[{self.__class__.__name__}._derive_ghost_strategy] - Full traceback: {traceback.format_exc()}")
        return None
