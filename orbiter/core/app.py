# orbiter/core/app.py

import logging
import time
import traceback
import threading
from orbiter.core.app_builder import AppBuilder
from orbiter.core.engine.builder.engine_factory import EngineFactory
from orbiter.core.reporting_service import ReportingService
from orbiter.core.auth_service import AuthService
from orbiter.core.ancillary_service import AncillaryServiceManager

logger = logging.getLogger("ORBITER")


class OrbiterApp:
    def __init__(self, project_root: str, context: dict):
        self.ctx = AppBuilder.build(project_root, context)
        self._running = threading.Event()
        self._running.set()
        self.initialized = False
        self.logged_in = False
        self._services = AncillaryServiceManager(self)
        self._services.register(ReportingService(self))

    def start(self):
        logger.info(self.ctx.constants.get('constants', 'app_started_msg', "🚀 Machine Started"))
        # Run initial setup before entering main loop
        self.setup()
        self._services.start_all()
        self.run()

    def run(self):
        logger.debug("Entering main application loop.")
        try:
            while self._running.is_set():
                logger.debug("Evaluating system rules.")
                primed = self.ctx.engine.state.primed if self.ctx.engine and self.ctx.engine.state else False
                logger.debug(f"State: Init={self.ctx.initialized}, Login={self.ctx.logged_in}, Primed={primed}")

                app_context = self.ctx.constants.get('factContexts', 'app_context')
                facts = self.ctx.rule_manager.evaluate(source=self, context=app_context)
                self.ctx.action_manager.execute_batch(facts)

                loop_interval = self.ctx.constants.get('app_settings', 'loop_interval_seconds', 5)
                time.sleep(loop_interval)
        except Exception as e:
            logger.critical(self.ctx.constants.get('constants', 'app_crash_msg', "💥 App Crash: {error}\n{traceback}").format(error=e, traceback=traceback.format_exc()))
            if hasattr(self.ctx, 'engine') and self.ctx.engine and hasattr(self.ctx.engine, 'shutdown'):
                self.ctx.engine.shutdown(str(e))
        finally:
            logger.info(self.ctx.constants.get('constants', 'app_stopped_msg', "🛑 Machine Stopped"))

    def stop(self):
        logger.debug("Stop requested.")
        self._running.clear()
        self._services.stop_all()
        if hasattr(self.ctx, 'engine') and self.ctx.engine and hasattr(self.ctx.engine, 'shutdown'):
            self.ctx.engine.shutdown("User initiated stop")

    def setup(self):
        logger.debug("Setting up engine.")
        try:
            # Derive real_broker_trade from mode
            mode = self.ctx.context.get('mode', 'simulation')
            real_broker_trade = (mode == 'live')
            mock_data = (mode == 'simulation')
            
            engine = EngineFactory.build_engine(
                self.ctx.session_manager,
                self.ctx.action_manager,
                real_broker_trade=real_broker_trade,
                mock_data=mock_data,
                context=self.ctx.context,
            )
            
            AppBuilder.setup_engine(self.ctx, engine, self)
            self.initialized = True
            logger.info(self.ctx.constants.get('constants', 'engine_initialized_msg', "✅ Engine initialized."))
            return True
        except Exception as e:
            logger.critical(self.ctx.constants.get('constants', 'setup_failed_msg', "❌ Setup failed: {error}").format(error=e))
            logger.critical(traceback.format_exc())
            return False

    def login(self):
        self.ctx.logged_in = AuthService.login(self.ctx.engine)
        self.logged_in = self.ctx.logged_in  # Sync with app attribute
        return self.ctx.logged_in
