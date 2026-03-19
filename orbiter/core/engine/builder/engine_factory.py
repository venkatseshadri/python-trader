# orbiter/core/engine/factory.py

import os
import logging
from orbiter.core.broker import BrokerClient
from orbiter.core.broker.mock_client import MockBrokerClient
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
    def build_engine(session_manager: SessionManager, action_manager: ActionManager, paper_trade: bool = True, context: dict = None):
        logger.debug(f"[{EngineFactory.__name__}.build_engine] - Starting engine build process.")
        constants = ConstantsManager.get_instance()
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
            'paper_trade': paper_trade,
            'verbose_logs': True
        }
        logger.debug(f"[{EngineFactory.__name__}.build_engine] - Merged full configuration: {full_config}")

        # 3. Initialize Core Components
        use_mock = context.get('mock_data', False) if context else False
        mock_data_file = context.get('mock_data_file') if context else None
        
        if use_mock:
            logger.info(f"[{EngineFactory.__name__}.build_engine] - Using MOCK broker (mock_data=true)")
            
            # Set environment variable for mock broker to pick up custom file
            if mock_data_file:
                import os
                os.environ['ORBITER_MOCK_DATA_FILE'] = mock_data_file
                logger.info(f"[{EngineFactory.__name__}.build_engine] - Using mock data file: {mock_data_file}")
            
            client = MockBrokerClient(session_manager.project_root, segment_name=seg_name)
            
            # Prime with mock data
            if universe:
                client.prime_candles(universe, lookback_mins=300)  # 300 mins = ~60 candles for ADX warmup
        else:
            client = BrokerClient(session_manager.project_root, segment_name=seg_name, paper_trade=paper_trade)
            logger.debug(f"[{EngineFactory.__name__}.build_engine] - BrokerClient initialized.")
            
            # Hardcoded NIFTY token mappings only for real broker
            client.master.TOKEN_TO_SYMBOL['51714'] = constants.get('magic_strings', 'token_to_symbol_nifty_51714')
            client.master.TOKEN_TO_SYMBOL['NFO|51714'] = constants.get('magic_strings', 'token_to_symbol_nfo_51714')
            logger.debug(f"[{EngineFactory.__name__}.build_engine] - Hardcoded NIFTY token mappings applied.")
        
        state = StateManager(client, universe, full_config, segment_name=seg_name, clear_paper_positions=context.get('clear_paper_positions', False) if context else False)
        logger.debug(f"[{EngineFactory.__name__}.build_engine] - StateManager initialized.")
        
        from orbiter.bot.sheets import log_buy_signals, log_closed_positions, update_active_positions, update_engine_state, get_engine_state
        executor = ActionExecutor(state)
        syncer = Syncer(update_active_positions, update_engine_state, get_engine_state)
        logger.debug(f"[{EngineFactory.__name__}.build_engine] - ActionExecutor and Syncer initialized.")

        # 4. Finalize State and Linkages
        
        state.load_session()
        state.sync_with_broker()
        logger.debug(f"[{EngineFactory.__name__}.build_engine] - Session loaded and synced with broker.")
        
        print(constants.get('magic_strings', 'universe_loaded_msg').format(count=len(universe), segment=seg_name.upper()))
        trade_score_key = global_config_schema.get('trade_score_key', 'trade_score')
        print(constants.get('magic_strings', 'entry_threshold_msg').format(threshold=full_config.get(trade_score_key)))

        logger.info(f"[{EngineFactory.__name__}.build_engine] - Engine build process complete. Returning Engine instance.")
        return Engine(state, session_manager, action_manager)
