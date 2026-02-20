# 🧠 Technical Design: Segment-Strict Scrip Resolution

**Date:** 2026-02-20  
**Status:** Implemented (Commit `a787fd2`)  
**Objective:** Prevent cross-segment master file "leaks" that cause the MCX session to stall while downloading 200MB NFO master files.

---

## 1. The Problem: "The NFO Pause"
During MCX sessions (Evening), if a commodity symbol (e.g., LEADMINI) failed to resolve its expiry, the `ContractResolver` was hardcoded to refresh BOTH NFO and MCX master files.
- **Impact:** The bot would pause its scanning loop for 2-3 minutes while downloading the massive NFO Derivative Master, even though it was trading MCX.
- **Consequence:** Missed entries and stale logs during highly volatile commodity moves.

---

## 2. Technical Modifications (`orbiter/core/broker/resolver.py`)

### A. Segment Detection
The `_select_expiry` and `_get_option_rows` methods now detect the required exchange based on the instrument type:
- `OPTCOM` / `FUTCOM` -> Targets **MCX**.
- Everything else -> Targets **NFO**.

### B. Isolated Refresh
When an emergency master refresh is triggered:
- The bot now calls `self.master.download_scrip_master(target_exch)`.
- This ensures that an MCX failure only refreshes the lightweight MCX master (~1MB), not the NFO behemoth (~200MB).

---

## 3. Design Outcome
- **Session Continuity:** MCX scanning remains fast and uninterrupted.
- **Network Efficiency:** Reduced data usage on the Raspberry Pi by 99% during commodity sessions.
- **Operational Speed:** Emergency refreshes now complete in < 5 seconds instead of 3 minutes.
