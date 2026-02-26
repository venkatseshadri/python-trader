#!/usr/bin/env python3

import argparse
import subprocess
import sys

def monitor_logs(host, user, password, log_file_path, patterns):
    """Connects to a remote host via SSH and searches for specified patterns in a log file."""
    try:
        # Construct the grep command for multiple patterns
        # We use | as a separator for grep -E, but need to escape it for the remote shell
        # Also need to handle patterns that might contain special characters.
        # For simplicity, let's assume patterns are basic regex for now.
        # If patterns themselves contain spaces or quotes, this will need more robust escaping.
        escaped_patterns = [p.replace("'", "'''") for p in patterns] # Basic escaping for single quotes
        grep_pattern = "|".join(escaped_patterns)

        # Construct the full remote command
        # Using bash -c to execute the command string remotely
        # Using cat and grep to search the file.
        # Redirecting stderr to stdout (2>&1) to capture all output.
        remote_command = f"cat {log_file_path} | grep -E '{grep_pattern}' 2>&1"

        # Construct the sshpass command
        ssh_command = [
            "sshpass",
            "-p", password,
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            f"{user}@{host}",
            "bash", "-c", remote_command
        ]

        print(f"[INFO] Running command: {' '.join(ssh_command)}", file=sys.stderr)

        # Execute the command
        result = subprocess.run(ssh_command, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            if result.stdout:
                print("--- Found Matches ---")
                print(result.stdout)
                print("---")
            else:
                print("No matches found.")
        elif result.returncode == 1: # grep returns 1 if no lines were selected
            print("No matches found.")
        else:
            print(f"Error executing command. Exit code: {result.returncode}", file=sys.stderr)
            print(f"Stderr: {result.stderr}", file=sys.stderr)
            print(f"Stdout: {result.stdout}", file=sys.stderr)

    except FileNotFoundError:
        print("Error: 'sshpass' command not found. Please ensure it is installed.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor remote log files for specified patterns.")
    parser.add_argument("--host", required=True, help="Hostname or IP address of the remote server (e.g., raspberrypi.local).")
    parser.add_argument("--user", required=True, help="SSH username (e.g., pi).")
    parser.add_argument("--password", required=True, help="SSH password.")
    parser.add_argument("--log-file-path", required=True, help="Absolute path to the log file on the remote server.")
    parser.add_argument("--patterns", required=True, nargs='+', help="List of regex patterns to search for (e.g., "SIM-FUTURE" "INFO.*Score").")

    args = parser.parse_args()

    monitor_logs(args.host, args.user, args.password, args.log_file_path, args.patterns)
