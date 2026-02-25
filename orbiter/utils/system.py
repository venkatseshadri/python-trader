# orbiter/utils/system.py

import os
import sys
import json
import subprocess
from datetime import datetime
from .data_manager import DataManager
from .argument_parser import ArgumentParser
from .constants_manager import ConstantsManager # Import ConstantsManager

# Constants (these will eventually come from ConstantsManager)
LOCK_ACQUIRE = "acquire"
LOCK_RELEASE = "release"

def resolve_project_root() -> str:
    """Calculates the project root relative to this file."""
    # This file is at: project_root/[APP_NAME]/utils/system.py
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def load_project_manifest(project_root: str) -> dict:
    """Loads the master project manifest (project.json) from the root."""
    return DataManager.load_manifest(project_root)

def bootstrap() -> str:
    """Resolves root and parses CLI facts in one step."""
    root = resolve_project_root()
    manifest = load_project_manifest(root)

    if not manifest:
        print(f"❌ BOOT ERROR: project.json missing at {root}")
        return root

    # Initialize ConstantsManager early
    ConstantsManager(root)

    # Parse CLI facts (side-effect only)
    ArgumentParser.parse_cli_to_facts(sys.argv[1:])

    return root

def load_system_config(project_root: str) -> dict:
    """Utility to load system-level configuration from the manifest-defined path."""
    manifest = load_project_manifest(project_root)
    rel_path = manifest.get('mandatory_files', {}).get('system_config')
    
    if rel_path:
        path = os.path.join(project_root, rel_path)
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception: pass
    return {}
