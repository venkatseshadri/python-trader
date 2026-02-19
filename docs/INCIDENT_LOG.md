# 🚨 Operational Incident Log

This document tracks major operational incidents, their root causes, resolutions, and post-mortem analysis for the Orbiter trading system.

---

## 📅 2026-02-19: Google Sheets Overflow & Crash Loop

**Severity:** Critical (System Outage)  
**Component:** `orbiter/bot/sheets.py` (Logging)  
**Duration:** ~20 minutes  

### 1. The Incident
**Symptom:**  
The Orbiter bot on the Raspberry Pi entered a crash loop, restarting every few seconds.
**Error Log:**  
`gspread.exceptions.APIError: [400]: This action would increase the number of cells in the workbook above the limit of 10000000 cells.`
**Root Cause:**  
The Google Spreadsheet hosting trade logs and scan metrics exceeded the maximum allowable size (10 million cells), causing the bot to crash whenever it attempted to append new data.

### 2. Resolution Steps
1.  **Diagnosis:** Confirmed via `tail -n 20 .../logs/system/orbiter_...log`.
2.  **Mitigation:** Executed the cleanup utility on the Raspberry Pi:
    ```bash
    cd /home/pi/python/python-trader
    echo 'y' | .venv/bin/python3 orbiter/utils/cleanup_sheets.py
    ```
3.  **Outcome:** Cleared `trade_log`, `active_positions`, `closed_positions`, and `scan_metrics`. Service resumed immediately.

### 3. Google Sheets Audit
To prevent recurrence, we audited the sheet usage.

| Sheet Name | Status | Usage Context | Action |
| :--- | :--- | :--- | :--- |
| **`trade_log`** | ✅ Active | Primary log for ALL trades. | **Keep & Clean** |
| **`active_positions`** | ✅ Active | Real-time tracking. | **Keep & Clean** |
| **`closed_positions`** | ✅ Active | History of squared-off positions. | **Keep & Clean** |
| **`scan_metrics_mcx`** | ✅ Active | High-freq scan logs for MCX. | **Keep & Clean** |
| **`scan_metrics_nfo`** | ✅ Active | High-freq scan logs for NFO. | **Keep & Clean** |
| **`control`** | ✅ Active | Runtime configuration. | **Keep (Do Not Clean)** |
| **`symbols`** | ✅ Active | Universe selection. | **Keep (Do Not Clean)** |
| `scan_metrics` | ⚠️ Partial | Default target, often overridden. | **Clean** |
| `summary` | ❌ Stale | Unused (Telegram only). | **Delete Manually** |
| `trade_log_mcx` | ❌ Stale | Unused. | **Delete Manually** |
| `active_positions_mcx` | ❌ Stale | Unused. | **Delete Manually** |
| `closed_positions_mcx` | ❌ Stale | Unused. | **Delete Manually** |
| `active_positions_nfo` | ❌ Stale | Unused. | **Delete Manually** |

### 4. Corrective Actions (Codebase)
*   **Updated `orbiter/utils/cleanup_sheets.py`:** Modified to explicitly include `scan_metrics_mcx` and `scan_metrics_nfo` in the cleanup routine, as these are the highest volume sheets.

---
