#!/usr/bin/env python3
"""
🚀 ORBITER - Universal Orchestrator Entry Point
"""
import os, sys, traceback

# 🔊 Logger setup (before imports)
from orbiter.utils.system import get_project_root
from orbiter.utils.logger import LOG_LEVELS
orbiter_log_level = os.environ.get("ORBITER_LOG_LEVEL", "INFO").upper()

# 🎯 Version
from orbiter.utils.version import load_version
print(f"✨ ORBITER v{load_version(get_project_root())} | PID: {os.getpid()}")

# 🚀 Imports
from orbiter.utils.system import bootstrap
from orbiter.utils.logger import setup_logging
from orbiter.utils.lock import manage_lockfile, LOCK_ACQUIRE, LOCK_RELEASE
from orbiter.core.app import OrbiterApp


def run_orchestrator():
    # 1. Pre-flight
    project_root, context = bootstrap()

    # 2. Boot Infrastructure
    logger = setup_logging(get_project_root(), log_level=orbiter_log_level)

    try:
        # 3. Acquire Lock
        manage_lockfile(project_root, LOCK_ACQUIRE)

        try:
            # 4. Execute
            app = OrbiterApp(project_root, context)
            app.start()
        finally:
            # 5. Cleanup
            manage_lockfile(project_root, LOCK_RELEASE)

    except Exception as e:
        logger.critical(f"💥 CRITICAL SYSTEM FAILURE: {e}\n{traceback.format_exc()}")
        raise


if __name__ == "__main__":
    run_orchestrator()
