# orbiter/core/engine/factory.py

import os
import logging
from orbiter.core.broker import BrokerClient
from orbiter.core.engine.session.state_manager import StateManager
from orbiter.core.engine.runtime.syncer import Syncer
from orbiter.core.engine.runtime.core_engine import Engine
from orbiter.core.engine.action.executor import ActionExecutor
from orbiter.core.engine.action.action_manager import ActionManager
from orbiter.utils.data_manager import DataManager
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.meta_config_manager import MetaConfigManager
from orbiter.core.engine.session.session_manager import SessionManager # Import SessionManager to access its methods

logger = logging.getLogger("ORBITER")

class EngineFactory:
    """
    Builds the unified trading engine using the DataManager for any file lookups.
    """
    @staticmethod
    def build_engine(session_manager: SessionManager, action_manager: ActionManager, simulation: bool = False, office_mode: bool = False):
        logger.debug(f"[{EngineFactory.__name__}.build_engine] - Starting engine build process.")
        constants = ConstantsManager.get_instance(session_manager.project_root)
        meta_config = MetaConfigManager.get_instance(session_manager.project_root)
        
        global_config_schema = meta_config.get_key('global_config_schema')
        project_manifest_schema = meta_config.get_key('project_manifest_schema')

        # Get seg_name from SessionManager's new interface
        seg_name = session_manager.get_active_segment_name()
        if not seg_name:
            logger.error(f"[{EngineFactory.__name__}.build_engine] - No active segment found from SessionManager. Cannot build engine.")
            raise ValueError("Cannot build engine without an active segment.")
        logger.debug(f"[{EngineFactory.__name__}.build_engine] - Active segment: {seg_name}")

        # 1. Load Universe via SessionManager (now gets from strategy bundle)
        universe = session_manager.get_active_universe()
        logger.debug(f"[{EngineFactory.__name__}.build_engine] - Loaded {len(universe)} symbols for universe from strategy bundle.")

        # 2. Load Global and Segment Configurations via DataManager and SessionManager
        global_config = DataManager.load_config(session_manager.project_root, project_manifest_schema.get('mandatory_files_key', 'mandatory_files'), 'global_config')
        
        # Segment config now comes directly from SessionManager (extracted from strategy bundle)
        segment_config = session_manager.get_segment_config() 
        
        full_config = {
            **global_config,
            **segment_config,
            'simulation': simulation,
            'office_mode': office_mode,
            'verbose_logs': True
        }
        logger.debug(f"[{EngineFactory.__name__}.build_engine] - Merged full configuration: {full_config}")

        # 3. Initialize Core Components
        broker_creds_path = DataManager.get_manifest_path(session_manager.project_root, project_manifest_schema.get('mandatory_files_key', 'mandatory_files'), 'broker_credentials')
        client = BrokerClient(session_manager.project_root, broker_creds_path, segment_name=seg_name)
        logger.debug(f"[{EngineFactory.__name__}.build_engine] - BrokerClient initialized with credentials from {broker_creds_path}.")
        
        state = StateManager(client, universe, full_config, segment_name=seg_name)
        logger.debug(f"[{EngineFactory.__name__}.build_engine] - StateManager initialized.")
        
        from orbiter.bot.sheets import log_buy_signals, log_closed_positions, update_active_positions, update_engine_state, get_engine_state
        executor = ActionExecutor(state)
        syncer = Syncer(update_active_positions, update_engine_state, get_engine_state)
        logger.debug(f"[{EngineFactory.__name__}.build_engine] - ActionExecutor and Syncer initialized.")

        # 4. Finalize State and Linkages 
        # TODO: These NIFTY mappings to be rule-driven or loaded from ScripMaster config.
        # For now, keeping as is, but acknowledging the hardcoding.
        client.master.TOKEN_TO_SYMBOL['51714'] = constants.get('magic_strings', 'token_to_symbol_nifty_51714')
        client.master.TOKEN_TO_SYMBOL['NFO|51714'] = constants.get('magic_strings', 'token_to_symbol_nfo_51714')
        logger.debug(f"[{EngineFactory.__name__}.build_engine] - Hardcoded NIFTY token mappings applied (TODO: make configurable).")
        
        state.load_session()
        state.sync_with_broker()
        logger.debug(f"[{EngineFactory.__name__}.build_engine] - Session loaded and synced with broker.")
        
        print(constants.get('magic_strings', 'universe_loaded_msg').format(count=len(universe), segment=seg_name.upper()))
        trade_score_key = global_config_schema.get('trade_score_key', 'trade_score')
        print(constants.get('magic_strings', 'entry_threshold_msg').format(threshold=full_config.get(trade_score_key)))

        logger.info(f"[{EngineFactory.__name__}.build_engine] - Engine build process complete. Returning Engine instance.")
        return Engine(state, session_manager, action_manager, office_mode)
