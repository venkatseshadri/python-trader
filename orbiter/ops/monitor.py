#!/usr/bin/env python3
"""
Orbiter Operations Agent
Monitors the Orbiter trading system for failures, restarts, and issues.
Sends alerts to Telegram when problems are detected.
"""

import os
import sys
import json
import time
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path

# Add orbiter to path for telegram notifier
sys.path.insert(0, '/home/trading_ceo/python-trader')
from orbiter.utils.telegram_notifier import send_telegram_msg

# Configuration
CONFIG = {
    "orbiter_home": "/home/trading_ceo/python-trader/orbiter",
    "data_dir": "/home/trading_ceo/python-trader/orbiter/data",
    "logs_dir": "/home/trading_ceo/python-trader/logs",
    "tmp_dir": "/tmp",
    "binary_path": "/home/trading_ceo/python-trader/dist/orbiter-4.6.1",
    "check_interval": 300,  # 5 minutes
    "max_log_age_hours": 6,  # Alert if no log updates in this time
}

# Error patterns to detect
ERROR_PATTERNS = {
    "scoring": r"Scoring Error|scoring error",
    "position_load": r"Failed to load paper positions",
    "crash": r"💥 App Crash",
    "exception": r"Exception|Traceback|Error:",
    "connection": r"Connection refused|timeout|network error",
    "auth": r"Authentication failed|invalid token|unauthorized",
}


def send_alert(message: str, priority: str = "normal"):
    """Send alert to Telegram."""
    try:
        emoji = {"critical": "🔴", "high": "🟠", "normal": "🟡", "low": "🔵"}
        full_msg = f"{emoji.get(priority, '⚠️')} <b>Orbiter Monitor</b>\n\n{message}"
        send_telegram_msg(full_msg)
        print(f"✅ Alert sent: {message[:50]}...")
    except Exception as e:
        print(f"❌ Error sending alert: {e}")


def get_log_age(strategy: str) -> dict:
    """Get age of log file for a strategy."""
    log_path = os.path.join(CONFIG["tmp_dir"], f"orbiter_{strategy}.log")
    
    if not os.path.exists(log_path):
        return {"exists": False, "age_minutes": None}
    
    mtime = os.path.getmtime(log_path)
    age_minutes = (time.time() - mtime) / 60
    
    return {
        "exists": True,
        "age_minutes": age_minutes,
        "last_modified": datetime.fromtimestamp(mtime).strftime("%H:%M"),
        "size_bytes": os.path.getsize(log_path)
    }


def check_process_running(strategy: str) -> bool:
    """Check if orbiter process is running for given strategy."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"orbiter.*{strategy}"],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except:
        return False


def parse_log_errors(strategy: str) -> list:
    """Parse log file for errors."""
    log_path = os.path.join(CONFIG["tmp_dir"], f"orbiter_{strategy}.log")
    errors = []
    
    if not os.path.exists(log_path):
        return errors
    
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()
            # Read last 100 lines
            recent_lines = lines[-100:] if len(lines) > 100 else lines
            
            for line in recent_lines:
                for error_type, pattern in ERROR_PATTERNS.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        errors.append({
                            "type": error_type,
                            "message": line.strip(),
                            "timestamp": extract_timestamp(line)
                        })
    except Exception as e:
        print(f"Error parsing log: {e}")
    
    return errors


def extract_timestamp(line: str) -> str:
    """Extract timestamp from log line."""
    patterns = [
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})",
        r"(\d{2}:\d{2}:\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    return ""


def get_paper_positions_status() -> dict:
    """Check paper positions file health."""
    path = os.path.join(CONFIG["data_dir"], "paper_positions.json")
    
    if not os.path.exists(path):
        return {"exists": False, "valid": False}
    
    try:
        with open(path) as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            return {"exists": True, "valid": False, "error": "Not a dict"}
        
        return {
            "exists": True,
            "valid": True,
            "positions_count": len(data.get("positions", [])),
            "last_update": data.get("last_updated", "unknown")
        }
    except json.JSONDecodeError as e:
        return {"exists": True, "valid": False, "error": str(e)}
    except Exception as e:
        return {"exists": True, "valid": False, "error": str(e)}


def check_system_health() -> dict:
    """Overall system health check."""
    health = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "strategies": {},
        "overall_status": "healthy",
        "alerts": []
    }
    
    # Check each strategy
    for strategy in ["n1", "n2", "s1", "s2", "m1"]:
        log_info = get_log_age(strategy)
        is_running = check_process_running(strategy)
        errors = parse_log_errors(strategy)
        
        strategy_status = {
            "log_exists": log_info["exists"],
            "log_age_minutes": log_info.get("age_minutes"),
            "last_modified": log_info.get("last_modified"),
            "is_running": is_running,
            "errors": errors
        }
        
        # Determine health
        if errors:
            health["alerts"].append(f"{strategy}: {len(errors)} error(s) found")
            health["overall_status"] = "error"
        
        if log_info["exists"] and log_info["age_minutes"]:
            if log_info["age_minutes"] > CONFIG["max_log_age_hours"] * 60:
                health["alerts"].append(f"{strategy}: No updates in {log_info['age_minutes']:.0f} min")
                if health["overall_status"] != "error":
                    health["overall_status"] = "warning"
        
        health["strategies"][strategy] = strategy_status
    
    # Check paper positions
    positions = get_paper_positions_status()
    health["paper_positions"] = positions
    
    if not positions["valid"]:
        health["alerts"].append(f"Paper positions: {positions.get('error', 'Invalid')}")
        health["overall_status"] = "error"
    
    return health


def generate_status_report(health: dict) -> str:
    """Generate human-readable status report."""
    lines = [
        f"📊 <b>Orbiter Status Report</b>",
        f"_{health['timestamp']}_",
        "",
    ]
    
    # Overall status
    status_icon = "✅" if health["overall_status"] == "healthy" else "⚠️"
    lines.append(f"{status_icon} <b>Status:</b> {health['overall_status'].upper()}")
    lines.append("")
    
    # Strategy status
    lines.append("<b>Strategies:</b>")
    for strat, info in health["strategies"].items():
        status_emoji = "🟢" if info["log_exists"] and info["log_age_minutes"] and info["log_age_minutes"] < 60 else "🔴"
        running = "🏃" if info["is_running"] else "💤"
        age = f"{info['log_age_minutes']:.0f}m" if info["log_age_minutes"] else "N/A"
        
        lines.append(f"  {status_emoji} {strat.upper()}: {running} | Log: {age} | Last: {info.get('last_modified', 'N/A')}")
        
        if info["errors"]:
            for err in info["errors"][:2]:
                msg = err['message'][:60].replace('[', '').replace(']', '')
                lines.append(f"     ⚠️ {msg}...")
    
    lines.append("")
    
    # Paper positions
    pp = health.get("paper_positions", {})
    lines.append(f"<b>Paper Positions:</b> {'✅ OK' if pp.get('valid') else '❌ ERROR'}")
    if pp.get("valid"):
        lines.append(f"   Positions: {pp.get('positions_count', 0)}")
    
    # Alerts
    if health["alerts"]:
        lines.append("")
        lines.append("<b>⚠️ Alerts:</b>")
        for alert in health["alerts"][:5]:
            lines.append(f"  • {alert}")
    
    return "\n".join(lines)


def restart_strategy(strategy: str) -> bool:
    """Attempt to restart a failed strategy."""
    try:
        # Kill existing process
        subprocess.run(["pkill", "-f", f"orbiter.*{strategy}"], capture_output=True)
        time.sleep(2)
        
        # Start fresh
        cmd = [CONFIG["binary_path"], "--strategyCode", strategy]
        subprocess.Popen(
            cmd,
            cwd=CONFIG["orbiter_home"],
            stdout=open(f"/tmp/orbiter_{strategy}.log", "w"),
            stderr=subprocess.STDOUT
        )
        
        send_alert(f"🔄 Auto-restarted {strategy.upper()}", "high")
        return True
    except Exception as e:
        send_alert(f"❌ Failed to restart {strategy}: {e}", "critical")
        return False


def run_monitoring_cycle():
    """Run one monitoring cycle."""
    print(f"\n{'='*50}")
    print(f"🔍 Orbiter Monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")
    
    health = check_system_health()
    
    # Print to console
    report = generate_status_report(health)
    print(report.replace("*", "").replace("_", ""))
    
    # Send alerts for issues
    if health["overall_status"] != "healthy":
        print("\n🚨 Sending alert...")
        priority = "high" if health["overall_status"] == "error" else "normal"
        send_alert(report, priority)
        
        # Try auto-restart for failed strategies
        for strat, info in health["strategies"].items():
            if info["errors"] and not info["is_running"]:
                print(f"\n🔄 Attempting restart of {strat}...")
                restart_strategy(strat)
    
    return health


def main():
    """Main entry point."""
    print("🤖 Orbiter Operations Agent Starting...")
    
    # Check if binary exists
    if not os.path.exists(CONFIG["binary_path"]):
        msg = f"Orbiter binary not found at {CONFIG['binary_path']}"
        print(f"❌ {msg}")
        send_alert(msg, "critical")
        sys.exit(1)
    
    # Send startup message
    send_alert("🤖 Orbiter Operations Agent started", "low")
    
    # Run monitoring cycle
    health = run_monitoring_cycle()
    
    # Send final status after a brief wait
    time.sleep(5)
    final_health = check_system_health()
    send_alert(generate_status_report(final_health), "normal")
    
    print("\n✅ Monitoring cycle complete")


if __name__ == "__main__":
    main()
