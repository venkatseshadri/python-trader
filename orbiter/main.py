#!/usr/bin/env python3
"""
🚀 ORBITER - Universal Orchestrator Entry Point
"""
import os
import sys
import logging
import traceback

# 🔊 Enable DEBUG logging for external APIs (Shoonya, WebSocket, urllib3)
logging.getLogger("NorenRestApiPy").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)
logging.getLogger("websocket").setLevel(logging.DEBUG)
logging.getLogger("websockets").setLevel(logging.DEBUG)

# 🌍 1. Path Resolution & Environment Setup
# This file is at project_root/orbiter/main.py
base_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(base_dir)

# Add project_root to sys.path to allow absolute 'orbiter.' imports
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from orbiter.utils.system import bootstrap
from orbiter.utils.logger import setup_logging
from orbiter.utils.lock import manage_lockfile, LOCK_ACQUIRE, LOCK_RELEASE
from orbiter.utils.argument_parser import ArgumentParser
from orbiter.core.app import OrbiterApp

def run_orchestrator():
    """
    Lean orchestration sequence with absolute imports.
    """
    # 🌍 2. Pre-flight
    bootstrap() # Ensures project.json exists

    # 📊 3. Parse Arguments into Facts
    context = ArgumentParser.parse_cli_to_facts(sys.argv[1:], project_root=project_root)

    # 🚀 4. Boot Infrastructure
    log_level = os.environ.get("ORBITER_LOG_LEVEL")
    logger = setup_logging(project_root, log_level=log_level) if log_level else setup_logging(project_root)
    
    try:
        # 🛡️ 5. Acquire Lock
        manage_lockfile(project_root, LOCK_ACQUIRE)
        
        try:
            # 🕹️ 6. Execute Machine
            OrbiterApp(project_root, context).run()
        finally:
            # 7. Guaranteed Clean up
            manage_lockfile(project_root, LOCK_RELEASE)
            
    except Exception as e:
        logger.critical(f"💥 CRITICAL SYSTEM FAILURE: {e}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    run_orchestrator()
