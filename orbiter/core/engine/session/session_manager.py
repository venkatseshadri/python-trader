# orbiter/core/engine/session/session_manager.py

import os
import pytz
from datetime import datetime, time as dt_time
import logging
from orbiter.utils.data_manager import DataManager
from orbiter.utils.schema_manager import SchemaManager
from orbiter.utils.constants_manager import ConstantsManager

logger = logging.getLogger("ORBITER")

class SessionManager:
    def __init__(self, project_root: str, paper_trade: bool = False, strategy_id: str = None):
        self.project_root = project_root
        self.constants = ConstantsManager.get_instance(project_root)
        self.schema_manager = SchemaManager.get_instance(project_root)
        
        # 1. Load Root Configs
        self.session_config = DataManager.load_config(project_root, 'mandatory_files', 'session_config')
        self.exchange_config = DataManager.load_config(project_root, 'mandatory_files', 'exchange_config')
        
        # 2. Load Strategy (The 'strategy.json')
        s_schema = self.schema_manager.get_key('session_schema') or {}
        
        # 🚀 Runtime Strategy Override: CLI Arg -> Env Var -> Config default
        rel_path = strategy_id
        if not rel_path or rel_path == 'default':
            rel_path = os.environ.get("ORBITER_STRATEGY")
        if not rel_path:
            rel_path = self.session_config.get(s_schema.get('active_strategy_path_key', 'active_strategy_path'))
        
        # Ensure it points to strategy.json if only a folder was given
        if rel_path and not rel_path.endswith('.json'):
            rel_path = os.path.join(rel_path, 'strategy.json')

        manifest = DataManager.load_manifest(self.project_root)
        structure = manifest.get('structure', {})

        # Fallbacks if schema entries are missing
        strat_base = self.schema_manager.get_key('project_manifest_schema', 'structure_key') or 'structure'
        strat_path_val = self.schema_manager.get_key(strat_base, 'strategies') or structure.get('strategies')
        if strat_path_val is None:
            strat_path_val = 'orbiter/strategies'

        full_strategy_path = os.path.join(self.project_root, strat_path_val, rel_path)
        self.strategy_dir = os.path.dirname(full_strategy_path)
        self.strategy_bundle = DataManager.load_json(full_strategy_path)
        
        # 3. 🧪 Load Filters from separate file
        f_key = self.schema_manager.get_key('strategy_schema', 'files_key')
        filter_file_key = self.schema_manager.get_key('strategy_schema', 'filters_file_key', 'filters_file')
        filter_rel = self.strategy_bundle.get(f_key, {}).get(filter_file_key)
        self.filters = DataManager.load_json(os.path.join(self.project_root, filter_rel)) if filter_rel else {}
        
        # 4. Resolve Operational Environment
        exch_id = self.strategy_bundle.get(self.schema_manager.get_key('strategy_schema', 'exchange_id_key'))
        self.op_config = self.exchange_config.get(exch_id, {}).copy()
        
        local_override = os.path.join(self.strategy_dir, "overrides", "exchange_config.json")
        if os.path.exists(local_override):
            self.op_config.update(DataManager.load_json(local_override).get(exch_id, {}))
            
        logger.info(f"🚀 Loaded: {self.strategy_bundle.get('name')} with {len(self.filters)} filter groups.")

    def get_session_facts(self) -> dict:
        import os
        ist = pytz.timezone('Asia/Kolkata')
        now = datetime.now(ist).time()
        m_start = dt_time.fromisoformat(self.op_config.get("market_start", "09:15:00"))
        m_end = dt_time.fromisoformat(self.op_config.get("market_end", "15:30:00"))
        t_start = dt_time.fromisoformat(self.op_config.get("trade_start", m_start.isoformat()))
        t_end = dt_time.fromisoformat(self.op_config.get("trade_end", "15:15:00"))
        
        # Override: Force market open if environment variable set
        force_open = os.environ.get("ORBITER_SIMULATE_MARKET_HOURS", "false").lower() == "true"
        
        return {
            "session.is_open": force_open or (m_start <= now < m_end),
            "session.is_trade_window": force_open or (t_start <= now < t_end),
            "session.is_eod": False, # 🔥 HARDCODED FALSE FOR TESTING
            "session.time": now.strftime("%H:%M:%S")
        }

    def get_active_segment_name(self) -> str:
        # segment_name is in plumbing.segment_name in exchange_config
        return self.op_config.get('plumbing', {}).get('segment_name', 'NFO').lower()

    def get_segment_config(self) -> dict:
        return self.op_config.get('plumbing', {})

    def get_active_rules_file(self) -> str:
        f_key = self.schema_manager.get_key('strategy_schema', 'files_key')
        r_key = self.schema_manager.get_key('strategy_schema', 'rules_file_key')
        return self.strategy_bundle.get(f_key, {}).get(r_key)

    def get_active_universe(self) -> list:
        f_key = self.schema_manager.get_key('strategy_schema', 'files_key')
        u_key = self.schema_manager.get_key('strategy_schema', 'instruments_file_key')
        rel = self.strategy_bundle.get(f_key, {}).get(u_key)
        return DataManager.load_json(os.path.join(self.project_root, rel))

    def get_all_strategy_parameters(self) -> dict:
        p_key = self.schema_manager.get_key('strategy_schema', 'strategy_parameters_key')
        return self.strategy_bundle.get(p_key, {})

    def hibernate(self, duration: int = 60):
        """Action: Pauses the application loop for a specified duration."""
        import time
        logger.info(self.constants.get('magic_strings', 'hibernate_msg', "💤 Hibernating for {duration}s").format(duration=duration))
        time.sleep(duration)
