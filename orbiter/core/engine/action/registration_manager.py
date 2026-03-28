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
    
    Supports multi-handler event types defined in constants.json.
    """
    def __init__(self, app: Any, engine: Any, session_manager: Any, action_manager: ActionManager, rule_manager: RuleManager):
        logger.debug(f"[{self.__class__.__name__}.__init__] - Initializing RegistrationManager.")
        self.app = app
        self.engine = engine
        self.session_manager = session_manager
        self.action_manager = action_manager
        self.rule_manager = rule_manager
        self.constants = ConstantsManager.get_instance()
        
        self._register_handlers_from_config()
        self._register_app_actions()
        self._register_fact_providers()
    
    def _register_handlers_from_config(self):
        """
        Register individual handler functions from constants.json config.
        This allows execute_event() to look up handlers by function name.
        """
        eventTypes = self.constants.get('eventTypes', {})
        
        for event_type, event_config in eventTypes.items():
            if isinstance(event_config, dict) and 'handlers' in event_config:
                for handler_config in event_config['handlers']:
                    func_name = handler_config.get('function')
                    if func_name and func_name not in self.action_manager.action_registry:
                        logger.debug(f"Registered handler placeholder: {func_name}")
        
        logger.debug("Handler config loaded from constants.json")

    def _register_app_actions(self):
        """Registers app-level actions with the ActionManager."""
        logger.debug(self.constants.get('constants', 'register_app_actions_msg'))
        if not self.app:
            logger.debug("No app instance; registering placeholder app actions.")
            # Register placeholder actions that will be updated when app is available
            self.action_manager.action_registry['app.setup'] = self._app_setup_placeholder
            self.action_manager.action_registry['app.login'] = self._app_login_placeholder
            self.action_manager.action_registry['app.prime_data'] = self._app_prime_data_placeholder
            self.action_manager.action_registry['app.stop'] = self._app_stop_placeholder
            return
        self.action_manager.action_registry[self.constants.get('eventTypes', 'app.setup')] = self.app.setup
        # prime_data is on engine, not app
        if self.engine and hasattr(self.engine, 'prime_data'):
            self.action_manager.action_registry['app.prime_data'] = self.engine.prime_data
        self.action_manager.action_registry[self.constants.get('eventTypes', 'app.stop')] = self.app.stop
        logger.debug(self.constants.get('constants', 'app_actions_registered_msg'))

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
            logger.debug(self.constants.get('constants', 'engine_not_ready_msg'))
            return

        logger.debug(self.constants.get('constants', 'register_engine_actions_msg'))
        if self.app:
            self.action_manager.action_registry[self.constants.get('eventTypes', 'app.login')] = self.app.login
        else:
            self.action_manager.action_registry[self.constants.get('eventTypes', 'app.login')] = self.engine.state.client.conn.login
        self.action_manager.action_registry[self.constants.get('eventTypes', 'engine.tick')] = self.engine.tick
        self.action_manager.action_registry[self.constants.get('eventTypes', 'engine.shutdown')] = self.engine.shutdown
        self.action_manager.action_registry[self.constants.get('eventTypes', 'session.hibernate')] = self.session_manager.hibernate
        
        self.action_manager.action_registry[self.constants.get('eventTypes', 'trade.place_spread')] = self.engine.action_logic.place_order
        self.action_manager.action_registry[self.constants.get('eventTypes', 'trade.place_future_order')] = self.engine.action_logic.place_order
        self.action_manager.action_registry[self.constants.get('eventTypes', 'trade.square_off_all')] = self.engine.action_logic.square_off_all
        self.action_manager.action_registry[self.constants.get('eventTypes', 'trade.send_alert')] = self.engine.action_logic.send_alert
        
        # Also register individual handler functions by name for multi-handler events
        self._register_individual_handlers()
        
        logger.debug(self.constants.get('constants', 'engine_actions_registered_msg'))
    
    def _register_individual_handlers(self):
        """Register individual handler functions for multi-handler event execution."""
        if not self.engine:
            return
        
        # Register app-level handlers
        if self.app:
            self.action_manager.action_registry['app.load_config'] = lambda **kwargs: self._handle_nop('app.load_config')
            self.action_manager.action_registry['app.initialize_logger'] = lambda **kwargs: self._handle_nop('app.initialize_logger')
            self.action_manager.action_registry['app.validate_credentials'] = lambda **kwargs: self._handle_nop('app.validate_credentials')
            self.action_manager.action_registry['app.authenticate_broker'] = lambda **kwargs: self._handle_nop('app.authenticate_broker')
            self.action_manager.action_registry['app.verify_connection'] = lambda **kwargs: self._handle_nop('app.verify_connection')
            self.action_manager.action_registry['app.fetch_broker_limits'] = lambda **kwargs: self._handle_nop('app.fetch_broker_limits')
            self.action_manager.action_registry['app.load_instrument_masters'] = lambda **kwargs: self._handle_nop('app.load_instrument_masters')
            self.action_manager.action_registry['app.build_symbol_mappings'] = lambda **kwargs: self._handle_nop('app.build_symbol_mappings')
            self.action_manager.action_registry['app.initialize_margin_calculator'] = lambda **kwargs: self._handle_nop('app.initialize_margin_calculator')
            self.action_manager.action_registry['app.save_session_state'] = lambda **kwargs: self._handle_nop('app.save_session_state')
            self.action_manager.action_registry['app.cleanup_resources'] = lambda **kwargs: self._handle_nop('app.cleanup_resources')
            self.action_manager.action_registry['app.send_shutdown_notification'] = lambda **kwargs: self._handle_nop('app.send_shutdown_notification')
        
        # Register engine-level handlers
        self.action_manager.action_registry['engine.update_market_data'] = lambda **kwargs: self._handle_nop('engine.update_market_data')
        self.action_manager.action_registry['engine.evaluate_entry_conditions'] = lambda **kwargs: self._handle_nop('engine.evaluate_entry_conditions')
        self.action_manager.action_registry['engine.evaluate_exit_conditions'] = lambda **kwargs: self._handle_nop('engine.evaluate_exit_conditions')
        self.action_manager.action_registry['engine.execute_trade_actions'] = lambda **kwargs: self._handle_nop('engine.execute_trade_actions')
        self.action_manager.action_registry['engine.update_portfolio_state'] = lambda **kwargs: self._handle_nop('engine.update_portfolio_state')
        self.action_manager.action_registry['engine.close_all_positions'] = self.engine.action_logic.square_off_all
        self.action_manager.action_registry['engine.save_engine_state'] = lambda **kwargs: self._handle_nop('engine.save_engine_state')
        self.action_manager.action_registry['engine.log_shutdown_reason'] = lambda **kwargs: self._handle_nop('engine.log_shutdown_reason')
        self.action_manager.action_registry['engine.send_shutdown_alert'] = self.engine.action_logic.send_alert
        self.action_manager.action_registry['session.pause_strategy'] = lambda **kwargs: self._handle_nop('session.pause_strategy')
        self.action_manager.action_registry['session.notify_hibernate'] = self.engine.action_logic.send_alert
        self.action_manager.action_registry['session.refresh_market_data'] = lambda **kwargs: self._handle_nop('session.refresh_market_data')
        self.action_manager.action_registry['session.resume_strategy'] = lambda **kwargs: self._handle_nop('session.resume_strategy')
        self.action_manager.action_registry['session.send_resume_notification'] = self.engine.action_logic.send_alert
        self.action_manager.action_registry['trade.validate_margin'] = lambda **kwargs: self._handle_nop('trade.validate_margin')
        self.action_manager.action_registry['trade.resolve_contracts'] = lambda **kwargs: self._handle_nop('trade.resolve_contracts')
        self.action_manager.action_registry['trade.calculate_spread_span'] = lambda **kwargs: self._handle_nop('trade.calculate_spread_span')
        self.action_manager.action_registry['trade.execute_spread_order'] = self.engine.action_logic.place_order
        self.action_manager.action_registry['trade.log_trade'] = lambda **kwargs: self._handle_nop('trade.log_trade')
        self.action_manager.action_registry['trade.update_portfolio'] = lambda **kwargs: self._handle_nop('trade.update_portfolio')
        self.action_manager.action_registry['trade.resolve_future_contract'] = lambda **kwargs: self._handle_nop('trade.resolve_future_contract')
        self.action_manager.action_registry['trade.calculate_future_margin'] = lambda **kwargs: self._handle_nop('trade.calculate_future_margin')
        self.action_manager.action_registry['trade.execute_future_order'] = self.engine.action_logic.place_order
        self.action_manager.action_registry['trade.get_open_positions'] = lambda **kwargs: self._handle_nop('trade.get_open_positions')
        self.action_manager.action_registry['trade.validate_square_off'] = lambda **kwargs: self._handle_nop('trade.validate_square_off')
        self.action_manager.action_registry['trade.execute_square_off_orders'] = self.engine.action_logic.square_off_all
        self.action_manager.action_registry['trade.confirm_all_closed'] = lambda **kwargs: self._handle_nop('trade.confirm_all_closed')
        self.action_manager.action_registry['trade.calculate_pnl'] = lambda **kwargs: self._handle_nop('trade.calculate_pnl')
        self.action_manager.action_registry['trade.log_square_off'] = lambda **kwargs: self._handle_nop('trade.log_square_off')
        self.action_manager.action_registry['trade.format_alert_message'] = lambda **kwargs: self._handle_nop('trade.format_alert_message')
        self.action_manager.action_registry['trade.send_telegram_alert'] = self.engine.action_logic.send_alert
        self.action_manager.action_registry['trade.log_alert'] = lambda **kwargs: self._handle_nop('trade.log_alert')
        
        logger.debug("Individual handlers registered for multi-handler events")
    
    def _handle_nop(self, handler_name, **kwargs):
        """No-op handler for unimplemented handlers."""
        logger.debug(f"[NOP] Handler: {handler_name} (not yet implemented)")
        return {'status': 'nop', 'handler': handler_name}

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
        logger.debug(self.constants.get('constants', 'register_fact_providers_msg'))
        
        # Global App Facts - use a method that looks up self.app at call time
        reg = self  # Capture self, not app
        self.rule_manager.register_provider(lambda: reg._get_app_facts())
        
        # Session Facts
        self.rule_manager.register_provider(self.session_manager.get_session_facts)
        
        # Engine Facts (Portfolio)
        if self.engine:
            self.rule_manager.register_provider(lambda: self.rule_manager.fact_calc.calculate_portfolio_facts(self.engine.state))

        logger.debug(self.constants.get('constants', 'fact_providers_registered_msg'))

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