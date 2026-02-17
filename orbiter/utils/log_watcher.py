import time
import os
import subprocess
from telegram_notifier import send_telegram_msg

# Configuration
LOG_DIR = "/home/pi/python/python-trader/logs/system"
KEYWORDS = ["ERROR", "CRITICAL", "FATAL", "Traceback"]

def get_latest_log_file():
    """Get the most recent orbiter log file."""
    files = [f for f in os.listdir(LOG_DIR) if f.startswith("orbiter_") and f.endswith(".log")]
    if not files:
        return None
    return os.path.join(LOG_DIR, sorted(files)[-1])

def watch_logs():
    """Tails the latest log file and looks for error keywords."""
    print(f"👀 Log Watcher started. Monitoring: {LOG_DIR}")
    
    current_log = get_latest_log_file()
    if not current_log:
        print("⚠️ No logs found yet. Waiting...")
        time.sleep(10)
        return

    # Start tailing the file
    process = subprocess.Popen(['tail', '-n', '0', '-f', current_log], 
                             stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE, 
                             text=True)

    try:
        while True:
            line = process.stdout.readline()
            if not line:
                # Check if a new log file was created (due to bot restart)
                new_log = get_latest_log_file()
                if new_log != current_log:
                    print(f"🔄 Switched to new log file: {new_log}")
                    process.terminate()
                    current_log = new_log
                    process = subprocess.Popen(['tail', '-n', '0', '-f', current_log], 
                                             stdout=subprocess.PIPE, 
                                             stderr=subprocess.PIPE, 
                                             text=True)
                continue

            # Check for keywords
            if any(keyword in line for keyword in KEYWORDS):
                print(f"🚨 Alert detected: {line.strip()}")
                clean_line = line.strip()
                send_telegram_msg(f"🚨 *Orbiter Alert Detected*:\n`{clean_line}`")
            
            time.sleep(0.1)

    except KeyboardInterrupt:
        process.terminate()
        print("👋 Watcher stopped.")

if __name__ == "__main__":
    while True:
        try:
            watch_logs()
        except Exception as e:
            print(f"Error in watcher: {e}")
            time.sleep(5)
