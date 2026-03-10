# orbiter/core/auth_service.py

import logging
import os

logger = logging.getLogger("ORBITER")


class AuthService:
    """Handles broker authentication."""

    @staticmethod
    def login(engine) -> bool:
        """Login to broker. 2FA handled internally."""
        if not engine:
            return False
        
        factor2 = os.environ.get("ORBITER_2FA")
        ok = engine.state.client.login(factor2_override=factor2)
        
        logged_in = bool(ok)
        logger.info(f"Login status updated: {logged_in}")
        return logged_in
