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
    """
    def __init__(self):
        logger.debug(f"[{self.__class__.__name__}.__init__] - Initializing ActionManager.")
        self.action_registry: Dict[str, Callable] = {}
        self.constants = ConstantsManager.get_instance()
        self.schema_manager = SchemaManager.get_instance()

    def register_action(self, action_type: str, handler: Callable):
        self.action_registry[action_type] = handler
        logger.debug(f"[{self.__class__.__name__}.register_action] - Registered action: {action_type}")

    def execute_batch(self, actions: List[Dict]):
        if not actions: return
        
        logger.debug(f"[{self.__class__.__name__}.execute_batch] - Processing {len(actions)} actions.")
        
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
