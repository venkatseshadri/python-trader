# orbiter/utils/system.py

import os
import sys
import json
import subprocess
from datetime import datetime
from .data_manager import ConfigLoader
from .argument_parser import ArgumentParser

LOCK_ACQUIRE = "acquire"
LOCK_RELEASE = "release"

PROJECT_ROOT: str | None = None
MANIFEST: dict = {}
CONSTANTS: dict = {}
GLOBAL_CONFIG: dict = {}

def get_project_root() -> str:
    """Get project root, initializing path if needed."""
    global PROJECT_ROOT
    if PROJECT_ROOT is None:
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

def bootstrap() -> tuple[str, dict]:
    """
    Early initialization: resolve root, load manifest, init constants, parse CLI.
    Runs before logging is set up.
    
    Returns:
        tuple: (project_root, context_dict)
    """
    global MANIFEST, CONSTANTS, GLOBAL_CONFIG
    project_root = get_project_root()
    
    MANIFEST = ConfigLoader.load_manifest(project_root)

    if not MANIFEST:
        print(f"❌ BOOT ERROR: manifest.json missing at {project_root}")
        return project_root, {}

    CONSTANTS = ConfigLoader.load_config(project_root, 'mandatory_files', 'constants')
    GLOBAL_CONFIG = ConfigLoader.load_config(project_root, 'mandatory_files', 'global_config')
    context = ArgumentParser.parse_cli_to_facts(sys.argv[1:], project_root=project_root)

    return project_root, context
