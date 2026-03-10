# orbiter/core/app_builder.py

import logging
from orbiter.core.engine.session.session_manager import SessionManager
from orbiter.core.engine.rule.rule_manager import RuleManager
from orbiter.core.engine.action.action_manager import ActionManager
from orbiter.core.engine.action.registration_manager import RegistrationManager
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager
from orbiter.utils.system import get_manifest

logger = logging.getLogger("ORBITER")


class AppContext:
    """Container for all app dependencies."""
    def __init__(self, project_root, context, session_manager, action_manager, rule_manager, registration_manager):
        self.project_root = project_root
        self.context = context
        self.session_manager = session_manager
        self.action_manager = action_manager
        self.rule_manager = rule_manager
        self.registration_manager = registration_manager
        self.engine = None
        self.initialized = False
        self.logged_in = False
        self.constants = ConstantsManager.get_instance()


class AppBuilder:
    """Builds and wires all app dependencies."""

    @staticmethod
    def build(project_root: str, context: dict) -> AppContext:
        """Build the application context with all dependencies."""
        logger.info("Building application context...")

        session_manager = SessionManager(
            project_root,
            context.get('paper_trade', False),
            strategy_id=context.get('strategyid'),
            context=context
        )
        
        action_manager = ActionManager()
        
        rules_path = get_manifest().get('mandatory_files', {}).get('system_rules')
        rule_manager = RuleManager(project_root, rules_path, session_manager)
        
        registration_manager = RegistrationManager(
            None, None, session_manager, action_manager, rule_manager
        )

        return AppContext(
            project_root=project_root,
            context=context,
            session_manager=session_manager,
            action_manager=action_manager,
            rule_manager=rule_manager,
            registration_manager=registration_manager
        )

    @staticmethod
    def setup_engine(ctx: AppContext, engine) -> None:
        """Wire up engine after it's built."""
        ctx.engine = engine
        ctx.initialized = True
        ctx.registration_manager.engine = engine
        ctx.registration_manager.update_registrations_for_engine()
