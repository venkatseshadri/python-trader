#!/usr/bin/env python3
"""
Bridge to Narasimha (Claude CLI) - Connector Layer

This module provides a secure bridge between Kubera (orchestrator) and 
Narasimha (Claude specialist) for delegated tasks.

Usage:
    from orbiter.utils.bridge import bridge_to_narasimha, set_claude_path
    
    # Set path manually if needed
    set_claude_path("/full/path/to/claude")
    
    # Call the bridge
    response = bridge_to_narasimha("Refactor the MAWM inbound logic")
"""

import subprocess
import json
import logging
import os
import shutil
import sys

# Configure logger
logger = logging.getLogger("KuberaOrchestrator")

# Claude CLI path - auto-discovered or set manually
CLAUDE_CLI_PATH = "/usr/local/bin/claude"


def set_claude_path(path):
    """
    Manually set Claude CLI path if auto-discovery fails.
    
    Usage:
        set_claude_path("/full/path/to/claude")
    """
    global CLAUDE_CLI_PATH
    CLAUDE_CLI_PATH = path
    logger.info(f"BRIDGE: Claude path manually set to {path}")


def _discover_claude_path():
    """Auto-discover Claude CLI path."""
    global CLAUDE_CLI_PATH
    
    if CLAUDE_CLI_PATH and os.path.exists(CLAUDE_CLI_PATH):
        return CLAUDE_CLI_PATH
    
    # Try common locations
    candidates = [
        "claude",
        "/usr/local/bin/claude",
        "/usr/bin/claude",
        "/home/trading_ceo/.local/bin/claude",
    ]
    
    for candidate in candidates:
        if shutil.which(candidate):
            CLAUDE_CLI_PATH = candidate
            logger.info(f"BRIDGE: Discovered Claude at {candidate}")
            return candidate
    
    return None


def bridge_to_narasimha(task_description, model=None):
    """
    Acts as the secure connector to the Narasimha (Claude) CLI.

    Args:
        task_description (str): The specific task or prompt for Narasimha.
        model (str): Model to use (opus, sonnet, haiku). Defaults to settings.json model.

    Returns:
        str: The response from Narasimha or an error message.
    """

    logger.info(f"BRIDGE ACTIVATED: Handing off to Narasimha (model={model or 'default'})")

    # Discover Claude path
    cli_path = _discover_claude_path()
    if not cli_path:
        error_msg = "BRIDGE ERROR: Claude CLI not found. Set manually with set_claude_path()."
        logger.error(error_msg)
        return error_msg

    # Build command: claude -p "task_description" [--model opus|sonnet|haiku]
    cmd = [cli_path, "-p", task_description]
    if model:
        cmd.extend(["--model", model])
    
    logger.info(f"BRIDGE: Running command: {' '.join(cmd)}")
    
    # Run and capture output
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd="/home/trading_ceo/python-trader"
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            error_msg = f"BRIDGE ERROR: CLI failed with status {result.returncode}. stderr: {result.stderr}"
            logger.error(error_msg)
            return error_msg
            
    except subprocess.TimeoutExpired:
        error_msg = "BRIDGE ERROR: Claude CLI timed out after 120 seconds"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"BRIDGE EXCEPTION: {str(e)}"
        logger.error(error_msg)
        return error_msg


# --- CLI Entry Point ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Bridge to Claude CLI")
    parser.add_argument("--task", type=str, required=True, help="Task description")
    parser.add_argument("--model", type=str, default=None, help="Model to use (opus, sonnet, haiku)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    result = bridge_to_narasimha(args.task, model=args.model)
    
    if args.json:
        print(json.dumps({"success": True, "result": result}))
    else:
        print(result)