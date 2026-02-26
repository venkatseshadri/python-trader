---
name: log-monitor
description: Monitors remote log files for specified patterns. Use when needing to check log files on remote systems like Raspberry Pi for specific trade signals or score changes.
---

# log-monitor Skill

## Instructions

This skill provides the capability to remotely monitor log files for specific patterns and report any findings. It is designed to be used when you need to check log files on remote systems, such as a Raspberry Pi, for specific trade signals or score changes without manually running commands.

### How to Use

Invoke this skill with the following parameters:

-   `rpi_host`: The hostname or IP address of the Raspberry Pi (e.g., `raspberrypi.local`).
-   `ssh_user`: The username for SSH access (e.g., `pi`).
-   `ssh_password`: The password for SSH access.
-   `log_file_path`: The absolute path to the log file on the Raspberry Pi (e.g., `python/python-trader/mcx_sim_run.log`).
-   `patterns`: A list of regular expression patterns to search for in the log file (e.g., `["SIM-FUTURE", "INFO.*Score"]`).

### Example Invocation

```python
# Assume the skill is loaded and available as `log_monitor_skill`

log_monitor_skill(
    rpi_host="raspberrypi.local",
    ssh_user="pi",
    ssh_password="raspberry",
    log_file_path="python/python-trader/mcx_sim_run.log",
    patterns=["SIM-FUTURE", "INFO.*Score"]
)
```

### Core Logic

The skill will execute the following steps:

1.  **Construct SSH Command**: It will build an SSH command using `sshpass` to connect to the specified `rpi_host` with the provided `ssh_user` and `ssh_password`.
2.  **Remote Log Search**: On the remote machine, it will use `cat` to read the `log_file_path` and `grep` to search for each pattern provided in the `patterns` list. The command will be structured to handle multiple patterns.
3.  **Report Findings**: If matches are found, it will display the matching lines. If no matches are found, it will report that no relevant entries were found.

**Note:** This skill assumes `sshpass` is installed on the local machine and that SSH key-based authentication is not configured or is not preferred for this operation.

## Bundled Resources

This skill does not require any bundled resources at this time.

## TODOs

- Add error handling for SSH connection failures.
- Implement a mechanism to handle very large log files efficiently.
- Consider adding support for `tail -f` for continuous monitoring (though this would require a different invocation strategy).
- Allow specifying glob patterns for log files.
- Add support for different remote shells or command execution methods if needed.
