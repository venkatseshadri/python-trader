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
        logger.info(self.ctx.constants.get('magic_strings', 'app_started_msg', "🚀 Machine Started"))
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

                app_context = self.ctx.constants.get('fact_contexts', 'app_context')
                facts = self.ctx.rule_manager.evaluate(source=self, context=app_context)
                self.ctx.action_manager.execute_batch(facts)

                loop_interval = self.ctx.constants.get('app_settings', 'loop_interval_seconds', 5)
                time.sleep(loop_interval)
        except Exception as e:
            logger.critical(self.ctx.constants.get('magic_strings', 'app_crash_msg', "💥 App Crash: {error}\n{traceback}").format(error=e, traceback=traceback.format_exc()))
            if hasattr(self.ctx, 'engine') and self.ctx.engine and hasattr(self.ctx.engine, 'shutdown'):
                self.ctx.engine.shutdown(str(e))
        finally:
            logger.info(self.ctx.constants.get('magic_strings', 'app_stopped_msg', "🛑 Machine Stopped"))

    def stop(self):
        logger.debug("Stop requested.")
        self._running.clear()
        self._services.stop_all()
        if hasattr(self.ctx, 'engine') and self.ctx.engine and hasattr(self.ctx.engine, 'shutdown'):
            self.ctx.engine.shutdown("User initiated stop")

    def setup(self):
        logger.debug("Setting up engine.")
        try:
            paper_trade = self.ctx.context.get('paper_trade', True)
            office_mode = self.ctx.context.get('office_mode', False)
            
            engine = EngineFactory.build_engine(
                self.ctx.session_manager,
                self.ctx.action_manager,
                paper_trade=paper_trade,
                office_mode=office_mode,
                context=self.ctx.context,
            )
            
            if office_mode:
                self._send_office_mode_signal()
            
            AppBuilder.setup_engine(self.ctx, engine, self)
            self.initialized = True
            logger.info(self.ctx.constants.get('magic_strings', 'engine_initialized_msg', "✅ Engine initialized."))
            return True
        except Exception as e:
            logger.critical(self.ctx.constants.get('magic_strings', 'setup_failed_msg', "❌ Setup failed: {error}").format(error=e))
            logger.critical(traceback.format_exc())
            return False

    def _send_office_mode_signal(self):
        from orbiter.utils.telegram_notifier import send_telegram_msg
        try:
            send_telegram_msg("🏢 <b>OFFICE MODE ACTIVE</b>\n\nMBP is taking over trading.\nFreezing RPI...")
            send_telegram_msg("/freeze")
            logger.info("📤 Sent freeze signal to RPI via Telegram")
        except Exception as e:
            logger.warning(f"Failed to send Telegram freeze: {e}")

    def login(self):
        self.ctx.logged_in = AuthService.login(self.ctx.engine)
        self.logged_in = self.ctx.logged_in  # Sync with app attribute
        return self.ctx.logged_in
