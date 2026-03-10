# orbiter/core/app.py
"""
ORBITER APPLICATION SEQUENCE:

STEP 1: __init__(project_root, context)
        └─> AppBuilder.build() 
            • Creates SessionManager (loads strategy from config)
            • Creates ActionManager  
            • Creates RuleManager
            • Creates RegistrationManager

STEP 2: start()
        └─> _start_reporting()     → Background thread for sheets
        └─> run()                  → Main loop

STEP 3: setup()                    → Called by rules engine
        └─> EngineBuilder.build()  → Build trading engine
            • Creates BrokerClient
            • Creates CoreEngine
            • Wires up registrations

STEP 4: login()                   → Called by rules engine
        └─> AuthService.login()   → Broker authentication

STEP 5: prime_data()              → Called by rules engine (now on Engine)
        └─> MarketData.prime_and_subscribe()
            • Start live WebSocket feed
            • Background load historical candles

MAIN LOOP: run()                  → Every 5 seconds
        └─> RuleManager.evaluate()  → Get facts
        └─> ActionManager.execute_batch() → Execute actions
"""

import logging
import time
import traceback
import threading
from orbiter.core.app_builder import AppBuilder
from orbiter.core.engine_builder import EngineBuilder
from orbiter.core.reporting_service import ReportingService
from orbiter.core.auth_service import AuthService
from orbiter.core.ancillary_service import AncillaryServiceManager

logger = logging.getLogger("ORBITER")


class OrbiterApp:
    """Main application orchestrator - focuses on run loop only."""

    # ========================================================================
    # STEP 1: Initialize
    # ========================================================================
    def __init__(self, project_root: str, context: dict):
        """
        STEP 1: Build all dependencies via AppBuilder
        - SessionManager (strategy config)
        - ActionManager (action execution)
        - RuleManager (rules engine)
        - RegistrationManager (action registration)
        """
        self.ctx = AppBuilder.build(project_root, context)
        self._running = threading.Event()
        self._running.set()
        self._services = AncillaryServiceManager(self)
        self._services.register(ReportingService(self))

    # ========================================================================
    # STEP 2: Start
    # ========================================================================
    def start(self):
        """STEP 2: Start application - kickoff services + main loop"""
        logger.info(self.ctx.constants.get('magic_strings', 'app_started_msg', "🚀 Machine Started"))
        self._services.start_all()
        self.run()                # Main loop

    # ========================================================================
    # MAIN LOOP
    # ========================================================================
    def run(self):
        """
        MAIN LOOP: Runs every 5 seconds
        - Evaluate rules to get facts
        - Execute actions based on facts
        """
        logger.debug("Entering main application loop.")

        try:
            while self._running.is_set():
                logger.debug(f"Evaluating system rules.")
                primed = self.ctx.engine.state.primed if self.ctx.engine else False
                logger.debug(f"State: Init={self.ctx.initialized}, Login={self.ctx.logged_in}, Primed={primed}")

                # Get facts from rule engine
                app_context = self.ctx.constants.get('fact_contexts', 'app_context')
                facts = self.ctx.rule_manager.evaluate(source=self, context=app_context)

                # Execute actions
                self.ctx.action_manager.execute_batch(facts)

                loop_interval = self.ctx.constants.get('app_settings', 'loop_interval_seconds', 5)
                time.sleep(loop_interval)
        except Exception as e:
            logger.critical(self.ctx.constants.get('magic_strings', 'app_crash_msg', "💥 App Crash: {error}\n{traceback}").format(error=e, traceback=traceback.format_exc()))
            if hasattr(self.ctx, 'engine') and self.ctx.engine and hasattr(self.ctx.engine, 'shutdown'):
                self.ctx.engine.shutdown(str(e))
        finally:
            logger.info(self.ctx.constants.get('magic_strings', 'app_stopped_msg', "🛑 Machine Stopped"))

    # ========================================================================
    # Lifecycle
    # ========================================================================
    def stop(self):
        """Stop the application."""
        logger.debug("Stop requested.")
        self._running.clear()
        self._services.stop_all()
        if hasattr(self.ctx, 'engine') and self.ctx.engine and hasattr(self.ctx.engine, 'shutdown'):
            self.ctx.engine.shutdown("User initiated stop")

    # ========================================================================
    # STEP 3: Setup (called by rules engine)
    # ========================================================================
    def setup(self):
        """
        STEP 3: Build trading engine
        - SessionManager already loaded strategy from config
        - Just build the engine
        """
        logger.debug("Setting up engine.")

        try:
            engine, session_manager = EngineBuilder.build(
                self.ctx.project_root,
                self.ctx.context,
                self.ctx.action_manager,
                self.ctx.session_manager
            )
            self.ctx.session_manager = session_manager
            AppBuilder.setup_engine(self.ctx, engine)
            logger.info(self.ctx.constants.get('magic_strings', 'engine_initialized_msg', "✅ Engine initialized."))
            return True
        except Exception as e:
            logger.critical(self.ctx.constants.get('magic_strings', 'setup_failed_msg', "❌ Setup failed: {error}").format(error=e))
            logger.critical(traceback.format_exc())
            return False

    # ========================================================================
    # STEP 4: Login (called by rules engine)
    # ========================================================================
    def login(self):
        """STEP 4: Broker authentication via AuthService"""
        self.ctx.logged_in = AuthService.login(self.ctx.engine)
        return self.ctx.logged_in
