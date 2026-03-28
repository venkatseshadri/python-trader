#!/usr/bin/env python3
"""
caller_detector.py - Detect how Orbiter was invoked
Usage: Import and call detect_caller() to get inference
"""

import os
import sys

def get_parent_name():
    """Get parent process name"""
    try:
        ppid = os.getppid()
        with open(f"/proc/{ppid}/comm", "r") as f:
            return f.read().strip()
    except:
        return "unknown"

def get_grandparent_name():
    """Get grandparent process name (the one that spawned the parent)"""
    try:
        ppid = os.getppid()
        with open(f"/proc/{ppid}/status", "r") as f:
            for line in f:
                if line.startswith("PPid:"):
                    gpid = int(line.split()[1])
                    with open(f"/proc/{gpid}/comm", "r") as gf:
                        return gf.read().strip()
    except:
        return "unknown"

def detect_caller():
    """
    Detect how this process was invoked based on process tree
    
    Returns:
        dict with:
        - inferred: bot/user/cron/manual/system
        - parent_name: what spawned this
        - grandparent_name: what spawned parent
        - source: where inference came from
    """
    parent = get_parent_name()
    grandparent = get_grandparent_name()
    
    # Inference rules
    inferred = "manual"
    source = "process_tree"
    
    # If --caller was explicitly passed, use that but verify
    if hasattr(sys, 'argv'):
        for arg in sys.argv:
            if arg.startswith('--caller='):
                explicit_caller = arg.split('=')[1]
                source = "cli_argument"
                return {
                    "inferred": explicit_caller,
                    "parent": parent,
                    "grandparent": grandparent,
                    "source": source,
                    "verified": True
                }
    
    # Process tree inference
    if grandparent in ['bash', 'sh', 'python3'] and parent in ['pybot.sh', 'pyuser.sh']:
        # Wrappers - derive from script name
        inferred = "bot" if "pybot" in parent else "user"
        source = f"wrapper_script:{parent}"
    elif parent in ['cron', 'crond']:
        inferred = "cron"
    elif grandparent in ['bash', 'sh'] and parent == 'python3':
        # Direct manual run: python3 orbiter/main.py
        inferred = "manual"
        source = "terminal"
    elif parent in ['systemd', 'init']:
        inferred = "system"
    elif 'python' in parent.lower():
        # Some Python script spawned it
        inferred = "script"
        source = "python_script"
    
    return {
        "inferred": inferred,
        "parent": parent,
        "grandparent": grandparent,
        "source": source,
        "verified": False
    }


if __name__ == "__main__":
    # Demo
    result = detect_caller()
    print(f"Detected caller: {result}")
    
    print(f"\n--- Process Tree ---")
    print(f"Grandparent: {result['grandparent']}")
    print(f"Parent:      {result['parent']}")
    print(f"Inferred:    {result['inferred']}")
    print(f"Source:      {result['source']}")