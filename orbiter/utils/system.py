import os
import sys
import json
import subprocess
from datetime import datetime
from .data_manager import ConfigLoader, DataManager
from .argument_parser import ArgumentParser

LOCK_ACQUIRE = "acquire"
LOCK_RELEASE = "release"

PROJECT_ROOT: str | None = None
MANIFEST: dict = {}
CONSTANTS: dict = {}
GLOBAL_CONFIG: dict = {}

# Lazy-loaded configs (loaded on demand, not at bootstrap)
SYSTEM_RULES: dict | None = None
FACT_DEFINITIONS: dict | None = None

def get_project_root() -> str:
    """Get project root, initializing path if needed."""
    global PROJECT_ROOT
    if PROJECT_ROOT is None:
        # Check if running as PyInstaller
        if getattr(sys, 'frozen', False):
            # Running as compiled binary
            # Use the directory containing the executable, not _MEIPASS
            # _MEIPASS is a temp dir that doesn't have our config files
            executable_dir = os.path.dirname(sys.executable)
            PROJECT_ROOT = os.path.dirname(executable_dir)
        else:
            PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)
    return PROJECT_ROOT

def get_manifest() -> dict:
    """Get loaded manifest."""
    return MANIFEST

def get_constants() -> dict:
    """Get loaded constants."""
    return CONSTANTS

def get_global_config() -> dict:
    """Get loaded global config."""
    return GLOBAL_CONFIG

def bootstrap(logger) -> tuple[str, dict]:
    """
    Early initialization: resolve root, load manifest, init constants, parse CLI.
    Must be called AFTER setup_logging() in main.py.
    
    Returns:
        tuple: (project_root, context_dict)
    """
    global MANIFEST, CONSTANTS, GLOBAL_CONFIG
    project_root = get_project_root()
    
    # Load manifest.json - this is the master registry of all config files
    MANIFEST = ConfigLoader.load_manifest(project_root)
    logger.debug(f"Manifest loaded: {list(MANIFEST.keys())}")

    if not MANIFEST:
        # Critical error - before logging available
        sys.exit(f"❌ BOOT ERROR: manifest.json missing at {project_root}")

    # Validate manifest - check all files exist
    validation = DataManager.validate_manifest(project_root, fail_on_missing_optional=False)
    if validation['mandatory_missing']:
        logger.error(f"❌ CRITICAL: {len(validation['mandatory_missing'])} mandatory files missing!")
        for f in validation['mandatory_missing']:
            logger.error(f"   - {f}")
        # Don't exit - let it try to run anyway (some features may work)

    # Load constants.json - trading parameters like ADX thresholds, spread widths
    CONSTANTS = ConfigLoader.load_config(project_root, 'mandatory_files', 'constants')
    logger.debug(f"Constants loaded: {list(CONSTANTS.keys())}")

    # Load global_config.json - optional, system-wide settings
    global_config_path = ConfigLoader.get_path(project_root, 'optional_files', 'global_config')
    if global_config_path:
        if os.path.exists(global_config_path):
            GLOBAL_CONFIG = ConfigLoader.load_json_file(global_config_path)
            logger.debug(f"Global config loaded: {list(GLOBAL_CONFIG.keys())}")
        else:
            # Path resolved but file doesn't exist - this is optional, log what it's for
            logger.info("📄 global_config.json not found (optional) - expected at orbiter/config/global_config.json")
            logger.info("   Purpose: Strategy-wide parameters (trade score thresholds, risk limits)")
            logger.info("   Example: orbiter/config/global_config.json.example")
            GLOBAL_CONFIG = {}
    else:
        # Path not in manifest - different error
        logger.warning("⚠️ global_config.json not in manifest (orbiter/config/global_config.json)")
        GLOBAL_CONFIG = {}
    
    # Parse CLI arguments to determine strategy code, debug mode, etc.
    context = ArgumentParser.parse_cli_to_facts(sys.argv[1:], project_root=project_root)
    # Filter to only meaningful CLI fields
    meaningful_context = {
        'mode': context.get('mode'),
        'strategyid': context.get('strategyid'),
        'caller': context.get('caller'),
        'loglevel': context.get('loglevel'),
    }
    # Add mock_data_file only if set
    if context.get('mock_data_file'):
        meaningful_context['mock_data_file'] = context.get('mock_data_file')
    logger.debug(f"CLI context: {meaningful_context}")

    logger.info(f"✨ Bootstrap complete | Root: {project_root}")
    return project_root, context


# ============================================================
# Lazy Loading Getters (for configs not needed at bootstrap)
# ============================================================

def get_system_rules() -> dict:
    """Lazy load system rules (only when rule engine needs it)."""
    global SYSTEM_RULES
    if SYSTEM_RULES is None:
        path = ConfigLoader.get_path(PROJECT_ROOT, 'mandatory_files', 'system_rules')
        if path:
            SYSTEM_RULES = ConfigLoader.load_json_file(path)
        else:
            SYSTEM_RULES = {}
    return SYSTEM_RULES


def get_fact_definitions() -> dict:
    """Lazy load fact definitions (only when fact calculator needs it)."""
    global FACT_DEFINITIONS
    if FACT_DEFINITIONS is None:
        path = ConfigLoader.get_path(PROJECT_ROOT, 'mandatory_files', 'fact_definitions')
        if path:
            FACT_DEFINITIONS = ConfigLoader.load_json_file(path)
        else:
            FACT_DEFINITIONS = {}
    return FACT_DEFINITIONS