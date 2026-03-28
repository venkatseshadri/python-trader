#!/usr/bin/env python3
"""
🚀 ORBITER - Universal Orchestrator Entry Point
"""
import os, sys, traceback, datetime, argparse

# Add project root to sys.path so we can import orbiter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Parse CLI arguments
parser = argparse.ArgumentParser(description="Orbiter - Trading Orchestrator")
parser.add_argument("--caller", default="null", help="Who triggered orbiter: bot, user, cron")
parser.add_argument("--logLevel", default="INFO", help="Log level: DEBUG, INFO, WARNING, ERROR, TRACE")
args, unknown = parser.parse_known_args()
caller = args.caller

# 🚀 Imports
from orbiter.utils.system import bootstrap, get_project_root
from orbiter.utils.logger import setup_logging
from orbiter.utils.lock import manage_lockfile, LOCK_ACQUIRE, LOCK_RELEASE
from orbiter.core.app import OrbiterApp
from orbiter.utils.caller_detector import detect_caller


def run_orchestrator():
    # 1. Setup logging FIRST (before any output)
    # CLI arg takes priority over env var
    cli_log_level = getattr(args, 'logLevel', None)
    orbiter_log_level = cli_log_level or os.environ.get("ORBITER_LOG_LEVEL", "INFO").upper()
    
    root = get_project_root()  # Get root path first
    logger = setup_logging(root, log_level=orbiter_log_level)
    
    # Log CLI args at INFO level (always, regardless of log level)
    logger.info(f"📋 CLI: caller={args.caller} logLevel={args.logLevel}")
    
    # 2. Pre-flight (with proper logging)
    from orbiter.utils.version import load_version
    logger.info(f"✨ ORBITER v{load_version(root)} | PID: {os.getpid()}")
    project_root, context = bootstrap(logger)
    
    # Log bootstrap results with DEBUG details
    from orbiter.utils.system import get_manifest, get_constants, get_global_config
    import getpass
    import pwd
    
    manifest = get_manifest()
    constants = get_constants()
    global_cfg = get_global_config()
    
    import json
    import time
    entry_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry_timezone = time.tzname[0]  # 'IST' on Linux
    try:
        process_user = pwd.getpwuid(os.getuid()).pw_name
    except:
        process_user = getpass.getuser()
    
    # Capture cwd BEFORE any chdir happens
    trigger_dir = os.getcwd()
    
    logger.debug(f"=== BOOTSTRAP RESULTS ===")
    logger.debug(f"project_root = {project_root}")
    logger.debug(f"manifest keys: {list(manifest.keys())}")
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
    
    logger.trace(f"{'=' * 60}")
    logger.trace(f"=== GLOBAL CONFIG ===")
    logger.trace(f"global_config keys: {list(global_cfg.keys())}")
    for section, data in global_cfg.items():
        logger.trace(f"  [{section}]:\n{json.dumps(data, indent=2)}")
    
    logger.trace(f"{'=' * 60}")
    logger.trace(f"=== CONSTANTS ===")
    logger.trace(f"constants keys: {list(constants.keys())}")
    for category, values in constants.items():
        logger.trace(f"\n--- {category} ---")
        logger.trace(f"{json.dumps(values, indent=4)}")
    
    logger.trace(f"{'=' * 60}")
    logger.trace(f"=== MANIFEST STRUCTURE ===")
    logger.trace(f"  structure:\n{json.dumps(manifest.get('structure', {}), indent=2)}")
    logger.trace(f"  mandatory_files:\n{json.dumps(list(manifest.get('mandatory_files', {}).keys()), indent=2)}")
    
    logger.trace(f"{'=' * 60}")
    logger.trace(f"=== ENTRY METADATA ===")
    logger.trace(f"  entry_time: {entry_time} {entry_timezone}")
    logger.trace(f"  caller: {caller}")
    
    # 🔍 Detect actual caller (parent process audit)
    caller_info = detect_caller()
    logger.trace(f"  caller_detected: {caller_info['inferred']}")
    logger.trace(f"  caller_parent: {caller_info['parent']}")
    logger.trace(f"  caller_grandparent: {caller_info['grandparent']}")
    logger.trace(f"  caller_source: {caller_info['source']}")
    
    # ⚠️ Alert if mismatch (explicit --caller differs from detected)
    if caller != "null" and caller != caller_info['inferred']:
        logger.warning(f"⚠️ CALLER MISMATCH: --caller={caller} but detected={caller_info['inferred']}")
    
    logger.trace(f"  process_user: {process_user}")
    logger.trace(f"  trigger_dir: {trigger_dir}")
    logger.trace(f"  pid: {os.getpid()}")
    logger.trace(f"  working_dir: {os.getcwd()}")
    
    # ✅ Validate Event System Configuration
    from orbiter.utils.validator import validate_event_system
    validation_result = validate_event_system(project_root, logger)
    if not validation_result['valid']:
        logger.error(f"❌ EVENT SYSTEM VALIDATION FAILED:")
        for err in validation_result['errors']:
            logger.error(f"   - {err}")
        raise ValueError("Event system configuration validation failed")
    logger.info(f"✅ Event system validated: {validation_result['event_count']} events, {validation_result['handler_count']} handlers")

    try:
        # 3. Acquire Lock
        manage_lockfile(project_root, LOCK_ACQUIRE, logger)

        try:
            # 4. Execute
            # app = OrbiterApp(project_root, context)
            # app.start()
            logger.info("🚀 OrbiterApp NOT started (commented out for testing)")
        finally:
            # 5. Cleanup
            manage_lockfile(project_root, LOCK_RELEASE, logger)

    except Exception as e:
        logger.critical(f"💥 CRITICAL SYSTEM FAILURE: {e}\n{traceback.format_exc()}")
        raise


if __name__ == "__main__":
    run_orchestrator()