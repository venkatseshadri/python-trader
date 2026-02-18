# ORBITER & SNIPER: Production Roadmap

## 🤖 Phase 1: Infrastructure & Basic Monitoring (DONE ✅)
- [x] **Telegram Integration:** 
    - [x] **Remote Error Watcher:** Tail system logs on RPi and ping Telegram for CRITICAL/ERROR status.
    - [x] **Trade Alerts:** Send real-time execution notifications to private channel.
    - [x] **Heartbeat Pings:** Daily check-in at market open to confirm the bot is alive.
- [x] **Emergency Kill-Switch (Manual):** Implemented via RPi shell access.
- [x] **Session Lifecycle:** Implemented Hibernation/Smart Rest to stop restart loops.
- [x] **MCX Integration:** Full futures mapping, lot size resolution, and automated config updates.

## 🔬 Phase 2: Filter Reverse Engineering (IN PROGRESS ⏳)
- [x] **Initial Study:** Completed 35-property analysis for ATGL (2025-12-03).
- [ ] **Mass Attribute Analysis:** Expand study to the entire `orbiter_revamp_data.csv`.
    - [ ] **Batch Processing:** Run analysis in 5 batches of ~21 stocks each.
    - [ ] **Consolidation:** Merge results into a master feature importance report.
- [ ] **Correlation Matrix:** Identify which indicators (ADX, RSI, EMA Slopes, ATR) have the highest "Predictive Power."
- [ ] **Filter Pruning:** Eliminate "Noise Filters" that don't add value.
- [ ] **Threshold Tuning:** Determine the "Sweet Spot" values (e.g., ADX > 25 vs ADX > 30).

## 📊 Phase 3: Validation & Sniper Refinement
- [ ] **Out-of-Sample Testing:** Run the new filter stack on 2024 data to prevent "overfitting."
- [ ] **Orbitron Shaded Graph:** Fix the Drawdown visualization in PDF/HTML reports (Revisit shaded area logic).
- [ ] **Vectorization Check:** Compare results between `vector_main.py` and `engine.py` to ensure 100% parity.
- [ ] **Slippage Simulation:** Add 0.05% - 0.1% artificial slippage to backtests.

## 🚀 Phase 4: Live Transition & Scaling
- [ ] **Live Mode:** Switch from `--simulation` to `Live Mode` for NFO/MCX.
- [ ] **Session Lifecycle:** Finalize auto-exit at 15:25 (NFO) and 23:25 (MCX).
- [ ] **Log Rotation:** Implement log rotation to prevent SD card overflow on Pi.

## 🛠️ Phase 5: DevOps & Integrity (DONE ✅)
- [x] **Portable Checksums:** Updated `release.sh` to use relative-path SHA-256 hashes.
- [x] **Automated Updates:** Verified `update.sh` loop over Tailscale.
- [x] **System Integrity:** Resolved 3482+ integrity check failures on Pi (Paths normalized & submodules excluded).

## 🕹️ Phase 6: Remote Command & Control (C2) (IN PROGRESS ⏳)
- [x] **Specification:** Completed in `docs/C2_SPECIFICATION.md`.
- [ ] **RuntimeConfig Manager:** Implement a thread-safe singleton to allow hot-reloading.
- [x] **Telegram Command Handler:** Implemented asynchronous background listener with callback support.
- [x] **Basic Commands:** Added `/margin` and `/status` for on-demand financial/operational snapshots.

## 📊 Phase 7: Automated Session Reporting (DONE ✅)
- [x] **Specification:** Completed in `docs/REPORTING_SPECIFICATION.md`.
- [x] **Pre-Session Report:** Automated fund/margin/position check at market open (NFO/MCX).
- [x] **Post-Session Debrief:** Comprehensive P&L and T+1 Margin report at market close.
- [x] **Real-time Margin Updates:** Automated "Post-Trade" margin snapshots sent to Telegram.
- [ ] **Performance Tracking:** Log session summaries to a local CSV/Database for weekly analysis.

---
*Last Updated: 2026-02-18*
