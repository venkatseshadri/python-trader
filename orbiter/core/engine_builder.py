# orbiter/core/engine_builder.py

import logging
from orbiter.core.engine.session.session_manager import SessionManager
from orbiter.core.engine.builder.engine_factory import EngineFactory
from orbiter.utils.telegram_notifier import send_telegram_msg

logger = logging.getLogger("ORBITER")


class EngineBuilder:
    """Builds and configures the trading engine."""

    @staticmethod
    def build(project_root: str, context: dict, action_manager, session_manager=None) -> tuple:
        """
        Build engine with configuration from context.
        
        Returns:
            tuple: (engine, session_manager)
        """
        paper_trade = context.get('paper_trade', True)
        office_mode = context.get('office_mode', False)

        if not session_manager:
            session_manager = SessionManager(
                project_root,
                paper_trade,
                strategy_id=context.get('strategyid')
            )

        engine = EngineFactory.build_engine(
            session_manager,
            action_manager,
            paper_trade=paper_trade,
            office_mode=office_mode,
        )

        if office_mode:
            EngineBuilder._send_office_mode_signal()

        return engine, session_manager

    @staticmethod
    def _send_office_mode_signal():
        """Send Telegram freeze signal to RPI."""
        try:
            send_telegram_msg("🏢 <b>OFFICE MODE ACTIVE</b>\n\nMBP is taking over trading.\nFreezing RPI...")
            send_telegram_msg("/freeze")
            logger.info("📤 Sent freeze signal to RPI via Telegram")
        except Exception as e:
            logger.warning(f"Failed to send Telegram freeze: {e}")
