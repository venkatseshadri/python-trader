# orbiter/core/engine/action/registration_manager.py

import logging
from typing import Any
from orbiter.core.engine.action.action_manager import ActionManager
from orbiter.core.engine.rule.rule_manager import RuleManager
from orbiter.utils.constants_manager import ConstantsManager

logger = logging.getLogger("ORBITER")

class RegistrationManager:
    """
    Centralized component for managing all Action and Fact registrations.
    It ensures that the ActionManager and RuleManager are properly
    wired with all available system capabilities.
    """
    def __init__(self, app: Any, engine: Any, session_manager: Any, action_manager: ActionManager, rule_manager: RuleManager):
        logger.debug(f"[{self.__class__.__name__}.__init__] - Initializing RegistrationManager.")
        self.app = app
        self.engine = engine
        self.session_manager = session_manager
        self.action_manager = action_manager
        self.rule_manager = rule_manager
        self.constants = ConstantsManager.get_instance()
        
        self._register_app_actions()
        self._register_fact_providers()
        
    def _register_app_actions(self):
        """Registers app-level actions with the ActionManager."""
        logger.debug(self.constants.get('magic_strings', 'register_app_actions_msg'))
        if not self.app:
            logger.debug("No app instance; registering placeholder app actions.")
            # Register placeholder actions that will be updated when app is available
            self.action_manager.action_registry['app.setup'] = self._app_setup_placeholder
            self.action_manager.action_registry['app.login'] = self._app_login_placeholder
            self.action_manager.action_registry['app.prime_data'] = self._app_prime_data_placeholder
            self.action_manager.action_registry['app.stop'] = self._app_stop_placeholder
            return
        self.action_manager.action_registry[self.constants.get('action_types', 'app_setup')] = self.app.setup
        # prime_data is on engine, not app
        if self.engine and hasattr(self.engine, 'prime_data'):
            self.action_manager.action_registry['app.prime_data'] = self.engine.prime_data
        self.action_manager.action_registry[self.constants.get('action_types', 'app_stop')] = self.app.stop
        logger.debug(self.constants.get('magic_strings', 'app_actions_registered_msg'))

    def _app_prime_data_placeholder(self, **kwargs):
        """Placeholder for app.prime_data - looks up app at call time."""
        if self.app and hasattr(self.app, 'prime_data'):
            return self.app.prime_data()
        logger.debug("app.prime_data placeholder called - waiting for app initialization")
    
    def _app_stop_placeholder(self, **kwargs):
        """Placeholder for app.stop - looks up app at call time."""
        if self.app and hasattr(self.app, 'stop'):
            return self.app.stop()
        logger.debug("app.stop placeholder called - waiting for app initialization")
    
    def _app_setup_placeholder(self, **kwargs):
        """Placeholder for app.setup - looks up app at call time."""
        if self.app and hasattr(self.app, 'setup'):
            return self.app.setup()
        logger.debug("app.setup placeholder called - waiting for app initialization")
    
    def _app_login_placeholder(self, **kwargs):
        """Placeholder for app.login - looks up app at call time."""
        if self.app and hasattr(self.app, 'login'):
            return self.app.login()
        logger.debug("app.login placeholder called - waiting for app initialization")

    def _register_engine_actions(self):
        """Registers engine-level actions with the ActionManager."""
        if not self.engine:
            logger.debug(self.constants.get('magic_strings', 'engine_not_ready_msg'))
            return

        logger.debug(self.constants.get('magic_strings', 'register_engine_actions_msg'))
        if self.app:
            self.action_manager.action_registry[self.constants.get('action_types', 'app_login')] = self.app.login
        else:
            self.action_manager.action_registry[self.constants.get('action_types', 'app_login')] = self.engine.state.client.conn.login
        self.action_manager.action_registry[self.constants.get('action_types', 'engine_tick')] = self.engine.tick
        self.action_manager.action_registry[self.constants.get('action_types', 'engine_shutdown')] = self.engine.shutdown
        self.action_manager.action_registry[self.constants.get('action_types', 'session_hibernate')] = self.session_manager.hibernate
        
        self.action_manager.action_registry[self.constants.get('action_types', 'trade_place_spread')] = self.engine.action_logic.place_order
        self.action_manager.action_registry[self.constants.get('action_types', 'trade_place_future_order')] = self.engine.action_logic.place_order
        self.action_manager.action_registry[self.constants.get('action_types', 'trade_square_off_all')] = self.engine.action_logic.square_off_all
        self.action_manager.action_registry[self.constants.get('action_types', 'trade_send_alert')] = self.engine.action_logic.send_alert
        
        logger.debug(self.constants.get('magic_strings', 'engine_actions_registered_msg'))

    def _get_app_facts(self):
        """Get app facts - looks up app at call time."""
        if self.app:
            try:
                return self.rule_manager.fact_calc.calculate_app_facts(self.app)
            except Exception as e:
                # App might not be fully initialized yet
                return {
                    "app.initialized": getattr(self.app, 'initialized', False),
                    "app.logged_in": getattr(self.app, 'logged_in', False),
                    "app.primed": False
                }
        return {
            "app.initialized": getattr(self.app, 'initialized', False) if self.app else False,
            "app.logged_in": getattr(self.app, 'logged_in', False) if self.app else False,
            "app.primed": False
        }
        
    def _register_fact_providers(self):
        """Registers all fact providers with the RuleManager."""
        logger.debug(self.constants.get('magic_strings', 'register_fact_providers_msg'))
        
        # Global App Facts - use a method that looks up self.app at call time
        reg = self  # Capture self, not app
        self.rule_manager.register_provider(lambda: reg._get_app_facts())
        
        # Session Facts
        self.rule_manager.register_provider(self.session_manager.get_session_facts)
        
        # Engine Facts (Portfolio)
        if self.engine:
            self.rule_manager.register_provider(lambda: self.rule_manager.fact_calc.calculate_portfolio_facts(self.engine.state))

        logger.debug(self.constants.get('magic_strings', 'fact_providers_registered_msg'))

    def update_registrations_for_engine(self):
        """
        Re-registers actions and fact providers that depend on the engine
        after the engine has been built/rebuilt.
        """
        logger.debug(f"[{self.__class__.__name__}.update_registrations_for_engine] - Updating registrations for engine.")
        self._register_engine_actions()
        
        # Update app.prime_data to use engine.prime_data (since it's on engine, not app)
        if self.engine and hasattr(self.engine, 'prime_data'):
            logger.debug("Registering app.prime_data -> engine.prime_data")
            self.action_manager.action_registry['app.prime_data'] = self.engine.prime_data
        
        # Clear and re-register fact providers to include engine-specific ones
        self.rule_manager.clear_providers()
        self._register_fact_providers()
