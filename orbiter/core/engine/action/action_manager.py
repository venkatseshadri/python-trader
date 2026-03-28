# orbiter/core/engine/action/action_manager.py

import logging
from typing import List, Dict, Any, Callable
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager

logger = logging.getLogger("ORBITER")

class ActionManager:
    """
    The Order Orchestrator. 
    Handles sorting, batching, and routing actions to the correct executor.
    Supports both single-handler and multi-handler event types.
    """
    def __init__(self):
        logger.debug(f"[{self.__class__.__name__}.__init__] - Initializing ActionManager.")
        self.action_registry: Dict[str, Callable] = {}
        self.constants = ConstantsManager.get_instance()
        self.schema_manager = SchemaManager.get_instance()

    def register_action(self, action_type: str, handler: Callable):
        self.action_registry[action_type] = handler
        logger.debug(f"[{self.__class__.__name__}.register_action] - Registered action: {action_type}")

    def register_actions(self, action_type: str, handlers: List[Callable]):
        """
        Register multiple handlers for a single action type.
        Handlers are executed in the order they are provided.
        """
        if action_type not in self.action_registry:
            self.action_registry[action_type] = []
        existing = self.action_registry[action_type]
        if isinstance(existing, list):
            self.action_registry[action_type] = existing + handlers
        else:
            self.action_registry[action_type] = [existing] + handlers
        logger.debug(f"[{self.__class__.__name__}.register_actions] - Registered {len(handlers)} handlers for: {action_type}")

    def execute_event(self, event_type: str, params: Dict[str, Any] = None):
        """
        Execute an event with multiple handlers (if defined in constants.json).
        Handlers are executed in priority order as defined in the config.
        """
        params = params or {}
        
        # Get event type config from constants
        event_config = self.constants.get('eventTypes', event_type)
        
        if not event_config:
            logger.warning(f"⚠️ No config found for event type: {event_type}")
            return self._execute_single(event_type, params)
        
        # Check if it's a multi-handler config (dict with 'handlers' key)
        if isinstance(event_config, dict) and 'handlers' in event_config:
            handlers_config = event_config['handlers']
            logger.info(f"🎯 Executing event: {event_type} with {len(handlers_config)} handlers")
            
            # Sort handlers by priority
            sorted_handlers = sorted(handlers_config, key=lambda h: h.get('priority', 999))
            
            results = []
            for handler_config in sorted_handlers:
                func_name = handler_config.get('function')
                required = handler_config.get('required', False)
                description = handler_config.get('description', '')
                
                logger.debug(f"  → Handler [{handler_config.get('priority')}]: {func_name} ({description})")
                
                # Look up the handler in registry
                handler = self.action_registry.get(func_name)
                if handler:
                    try:
                        result = handler(**params)
                        results.append({'function': func_name, 'success': True, 'result': result})
                    except Exception as e:
                        logger.error(f"  ❌ Handler {func_name} failed: {e}")
                        if required:
                            raise
                        results.append({'function': func_name, 'success': False, 'error': str(e)})
                else:
                    logger.warning(f"  ⚠️ Handler not found: {func_name}")
                    if required:
                        raise ValueError(f"Required handler not found: {func_name}")
                    results.append({'function': func_name, 'success': False, 'error': 'Handler not found'})
            
            return results
        else:
            # Single handler mode (backward compatible)
            return self._execute_single(event_type, params)
    
    def _execute_single(self, action_type: str, params: Dict[str, Any]):
        """Execute a single handler (backward compatible mode)."""
        handler = self.action_registry.get(action_type)
        if handler:
            try:
                return handler(**params)
            except Exception as e:
                logger.error(f"❌ Execution Error [{action_type}]: {e}")
                raise
        else:
            logger.warning(f"⚠️ No handler registered for: {action_type}")
            return None

    def execute_batch(self, actions: List[Dict]):
        if not actions: return
        
        logger.debug(f"[{self.__class__.__name__}.execute_batch] - Processing {len(actions)} actions.")
        
        for action in actions:
            logger.info(f"⚡ SYSTEM ACTION: {action.get('type')} | Params: {action.get('params')}")
        
        # 📏 1. SORT BY SEQUENCE
        # If 'sequence' is missing, it defaults to 999 (execute last)
        seq_key = self.schema_manager.get_key('rule_schema', 'sequence_key', 'sequence')
        try:
            sorted_actions = sorted(actions, key=lambda x: x.get(seq_key, 999))
        except Exception as e:
            logger.error(f"❌ Sort Error in execute_batch: {e}")
            sorted_actions = actions

        # 🚀 2. EXECUTE IN ORDER
        for action in sorted_actions:
            a_type = action.get('type')
            params = action.get('params', {})
            
            if a_type in self.action_registry:
                logger.debug(f"[{self.__class__.__name__}.execute_batch] - Executing: {a_type} (Seq: {action.get(seq_key, 'None')})")
                try:
                    self.action_registry[a_type](**params)
                except Exception as e:
                    logger.error(f"❌ Execution Error [{a_type}]: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
            else:
                logger.warning(f"⚠️ Unregistered Action Type: {a_type}")
