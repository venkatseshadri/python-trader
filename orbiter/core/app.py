# orbiter/core/app.py

import logging
import time
import traceback
import os
from orbiter.core.engine.session.session_manager import SessionManager
from orbiter.core.engine.builder.engine_factory import EngineFactory
from orbiter.core.engine.rule.rule_manager import RuleManager
from orbiter.core.engine.action.action_manager import ActionManager
from orbiter.core.engine.action.registration_manager import RegistrationManager
from orbiter.utils.data_manager import DataManager
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager # Import SchemaManager
from orbiter.utils.logger import setup_logging

logger = logging.getLogger("ORBITER")

class OrbiterApp:
    def __init__(self, project_root, context):
        self.project_root = project_root
        self.context = context 
        self.running = True
        self.engine = None
        self.initialized = False
        self.primed = False
        self.logged_in = False
        
        self.constants = ConstantsManager.get_instance(project_root)
        self.schema_manager = SchemaManager.get_instance(project_root) # Use SchemaManager
        self.global_schema = self.schema_manager.get_key('global_schema') # Use new schema name

        # 2. Load Global Config to get log_level
        global_config = DataManager.load_config(project_root, 'mandatory_files', 'global_config')
        log_level_key = self.global_schema.get('log_level_key', 'log_level') # Use schema_manager for key name
        configured_log_level = global_config.get(log_level_key, 'INFO')
        env_log_level = os.environ.get("ORBITER_LOG_LEVEL")
        if env_log_level:
            configured_log_level = env_log_level

        # 3. Setup logging
        setup_logging(project_root, log_level=configured_log_level)
        logger.info(self.constants.get('magic_strings', 'app_started_msg', "🚀 Generic Machine Started")) # Moved here after logging is setup

        # 4. Infrastructure
        self.session_manager = SessionManager(
            project_root, 
            context.get('paper_trade', False), 
            strategy_id=context.get('strategyid')
        )
        self.action_manager = ActionManager()
        
        # 5. Rule Hub
        rules_path = DataManager.get_manifest_path(project_root, 'mandatory_files', 'system_rules')
        self.rule_manager = RuleManager(project_root, rules_path, self.session_manager)

        # 6. Centralized Registration
        self.registration_manager = RegistrationManager(self, self.engine, self.session_manager, self.action_manager, self.rule_manager)
        self.last_scan_log_ts = 0
        self.last_active_strategy = None

    def login(self, **params):
        """Action: broker login with optional env-based 2FA override."""
        if not self.engine:
            return False
        factor2 = params.get('factor2') or os.environ.get("ORBITER_2FA")
        ok = self.engine.state.client.login(factor2_override=factor2)
        self.logged_in = bool(ok)
        logger.info(f"Login status updated: {self.logged_in}")
        return ok

    def _evaluate_dynamic_strategy(self):
        """Evaluate dynamic strategy config and select strategy based on market regime."""
        dynamic_config = self.context.get('dynamic_strategy_config')
        if not dynamic_config or not dynamic_config.get('enabled', False):
            return
        
        from orbiter.utils.yf_adapter import get_market_adx, get_market_regime
        
        # Get regime from Yahoo Finance
        regime = get_market_regime('SENSEX')
        adx = get_market_adx('SENSEX')
        
        logger.info(f"📊 Market Regime Check: SENSEX ADX = {adx} -> {regime.upper()}")
        
        # Select strategy based on regime
        strategies = dynamic_config.get('strategies', {})
        if regime == 'sideways':
            strategy = strategies.get('sideways', {})
        elif regime == 'trending':
            strategy = strategies.get('trending', {})
        else:
            strategy = strategies.get('trending', {})  # Default to trending
        
        if strategy:
            strategy_code = strategy.get('strategyCode')
            strategy_id = strategy.get('strategyId')
            logger.info(f"🎯 Dynamic Strategy Selected: {strategy_code or strategy_id} ({regime})")
            # Store selected strategy - will be used by engine
            self.context['selected_strategy_code'] = strategy_code
            self.context['selected_strategy_id'] = strategy_id

    def setup(self, **params):
        """Action: Builds the engine and registers its generic capabilities."""
        logger.debug(f"[{self.__class__.__name__}.setup] - Initializing engine components with params: {params}")
        
        # 🚀 Evaluate dynamic strategy BEFORE building engine
        dynamic_config = self.context.get('dynamic_strategy_config')
        selected_strategy_id = None
        if dynamic_config and dynamic_config.get('enabled'):
            self._evaluate_dynamic_strategy()
            selected_code = self.context.get('selected_strategy_code')
            selected_id = self.context.get('selected_strategy_id')
            if selected_code:
                # Resolve strategy code to full strategy ID
                from orbiter.utils.argument_parser import ArgumentParser
                selected_strategy_id = ArgumentParser._resolve_strategy(selected_code, self.project_root)
                logger.info(f"🔄 Restarting engine with strategy: {selected_code} -> {selected_strategy_id}")
        
        try:
            # Merge context with params, but pass only engine-supported kwargs.
            full_params = {**self.context, **params}
            engine_kwargs = {
                "paper_trade": bool(full_params.get("paper_trade", True)),
                "office_mode": bool(full_params.get("office_mode", False)),
            }
            dropped_keys = sorted(k for k in full_params.keys() if k not in engine_kwargs)
            if dropped_keys:
                logger.debug(f"Ignoring unsupported setup params: {dropped_keys}")

            # Rebuild session_manager if dynamic strategy selected new strategy
            if selected_strategy_id:
                self.session_manager = SessionManager(
                    self.project_root, 
                    self.context.get('paper_trade', True), 
                    strategy_id=selected_strategy_id
                )
            
            self.engine = EngineFactory.build_engine(
                self.session_manager,
                self.action_manager,
                **engine_kwargs,
            )
            
            # If office mode, send freeze signal to RPI
            if engine_kwargs.get("office_mode"):
                try:
                    from orbiter.utils.telegram_notifier import send_telegram_msg
                    send_telegram_msg("🏢 <b>OFFICE MODE ACTIVE</b>\n\nMBP is taking over trading.\nFreezing RPI...")
                    send_telegram_msg("/freeze")
                    logger.info("📤 Sent freeze signal to RPI via Telegram")
                except Exception as e:
                    logger.warning(f"Failed to send Telegram freeze: {e}")
            
            self.registration_manager.engine = self.engine
            self.registration_manager.update_registrations_for_engine()

            self.initialized = True
            logger.info(self.constants.get('magic_strings', 'engine_initialized_msg', "✅ Engine initialized successfully."))
            return True
        except Exception as e:
            logger.critical(self.constants.get('magic_strings', 'setup_failed_msg', "❌ Setup failed: {error}").format(error=e))
            logger.critical(traceback.format_exc())
            return False

    def prime_data(self, **params):
        """Action: Primes the market data for all symbols."""
        if not self.engine: return False
        try:
            logger.info("⚡ PRIMING DATA...")
            # Start Live Feed immediately
            self.engine.state.client.start_live_feed(self.engine.state.symbols)

            # 🔥 Mark primed immediately so engine.tick can start
            self.primed = True
            
            # 🔥 Run heavy history retrieval in a background thread
            import threading
            def _bg_prime():
                params = self.session_manager.strategy_bundle.get('strategy_parameters', {})
                lookback = params.get('priming_lookback_mins', 120)
                interval = params.get('priming_interval', 5)
                self.engine.state.client._priming_interval = interval
                self.engine.state.client.prime_candles(self.engine.state.symbols, lookback_mins=lookback)
                logger.info("✅ Background Data Priming Complete.")

            threading.Thread(target=_bg_prime, daemon=True).start()
            return True
        except Exception as e:
            logger.error(f"❌ Priming Failed: {e}")
            return False

    def _reporting_loop(self):
        """Dedicated thread for periodic Google Sheets reporting."""
        logger.info("📊 Reporting Thread Started.")
        while self.running:
            try:
                now_ts = time.time()
                if self.engine and self.initialized and (now_ts - self.last_scan_log_ts >= 60):
                    from orbiter.bot.sheets import log_scan_metrics
                    metrics = getattr(self.engine.state, 'last_scan_metrics', [])
                    if metrics:
                        # 🧹 Strategy Change Cleanup
                        current_strat = self.session_manager.strategy_bundle.get('name')
                        tab_name = f"scan_metrics_{self.engine.state.segment_name.lower()}"
                        
                        if self.last_active_strategy != current_strat:
                            try:
                                import gspread
                                from orbiter.bot.sheets import Credentials, SCOPE, _get_or_create_worksheet, SCAN_METRICS_HEADER
                                creds_path = os.path.join(self.project_root, "orbiter", "bot", "credentials.json")
                                creds = Credentials.from_service_account_file(creds_path, scopes=SCOPE)
                                client = gspread.authorize(creds)
                                book = client.open("trade_log")
                                sheet = _get_or_create_worksheet(book, tab_name)
                                sheet.clear()
                                sheet.insert_row(SCAN_METRICS_HEADER, 1)
                                logger.info(f"🧹 Cleared {tab_name} due to strategy switch: {current_strat}")
                                self.last_active_strategy = current_strat
                            except Exception as clear_err:
                                logger.error(f"⚠️ Sheet clear failed: {clear_err}")

                        logger.info(f"📊 Publishing {len(metrics)} scan metrics to Google Sheets [{tab_name}]...")
                        log_scan_metrics(metrics, tab_name=tab_name)
                        
                        # Also sync active positions
                        if hasattr(self.engine.state, 'syncer') and self.engine.state.syncer:
                            self.engine.state.syncer.sync_active_positions_to_sheets(self.engine.state)
                        
                        self.last_scan_log_ts = now_ts
            except Exception as e:
                logger.error(f"❌ Reporting Error: {e}")
            
            time.sleep(10) # Check every 10s if it's time to report

    def run(self):
        logger.debug(f"[{self.__class__.__name__}.run] - Entering main application loop.")
        
        # Start Reporting Thread
        import threading
        threading.Thread(target=self._reporting_loop, daemon=True).start()

        try:
            while self.running:
                logger.trace(f"[{self.__class__.__name__}.run] - Evaluating system rules.")
                
                # Get facts for logging state
                logger.trace(f"Current State: Init={self.initialized}, Login={self.logged_in}, Primed={self.primed}")

                actions = self.rule_manager.evaluate(source=self, context=self.constants.get('fact_contexts', 'app_context'))
                
                if actions:
                    for action in actions:
                        logger.info(f"⚡ SYSTEM ACTION: {action.get('type')} | Params: {action.get('params')}")
                
                logger.trace(f"[{self.__class__.__name__}.run] - Executing {len(actions)} system actions.")
                self.action_manager.execute_batch(actions)
                
                time.sleep(5)
        except Exception as e:
            logger.critical(self.constants.get('magic_strings', 'app_crash_msg', "💥 App Crash: {error}\n{traceback}").format(error=e, traceback=traceback.format_exc()))
            if self.engine: self.engine.shutdown(self.constants.get('magic_strings', 'crash_reason'))
        logger.info(self.constants.get('magic_strings', 'app_stopped_msg', "🛑 Machine Stopped"))

    def stop(self):
        logger.debug(f"[{self.__class__.__name__}.stop] - Stop requested.")
        self.running = False
