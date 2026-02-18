# ORBITER & SNIPER: Production Roadmap

## 🤖 Phase 1: Infrastructure & Basic Monitoring (DONE ✅)
- [x] **Telegram Integration:** Heartbeat, Alerts, and Error Watcher.
- [x] **Emergency Kill-Switch:** Manual RPi shell access.
- [x] **Session Lifecycle:** Hibernation/Smart Rest logic.
- [x] **MCX Integration:** Full futures mapping and lot size resolution.

## 🔬 Phase 2: Filter Reverse Engineering (IN PROGRESS ⏳)
- [x] **Initial Study:** Completed 35-property analysis for ATGL.
- [ ] **Mass Attribute Analysis:** Study entire `orbiter_revamp_data.csv` in batches.
- [ ] **Correlation Matrix:** Identify highest "Predictive Power" indicators.
- [ ] **Filter Pruning:** Eliminate low-value noise filters.

## 📊 Phase 3: Validation & Sniper Refinement
- [ ] **Out-of-Sample Testing:** 2024 backtest validation.
- [ ] **Orbitron Shaded Graph:** Fix drawdown visualization logic.
- [ ] **Vectorization Check:** Parity check between vector vs loop engines.

## 🚀 Phase 4: Live Transition & Scaling
- [ ] **Live Mode:** Shift from simulation to real execution.
- [ ] **Session Lifecycle:** Finalize auto-exit timings.
- [ ] **Log Rotation:** Automated RPi log maintenance.

## 🛠️ Phase 5: DevOps & Integrity (DONE ✅)
- [x] **Checksums:** Portable relative-path SHA-256 validation.
- [x] **Automated Updates:** Verified `update.sh` loop.
- [x] **System Integrity:** Resolved all path and submodule conflicts.

## 🕹️ Phase 6: Remote Command & Control (C2) (DONE ✅)
- [x] **Specification:** Reference `docs/C2_SPECIFICATION.md`.
- [x] **Telegram Command Handler:** Asynchronous background listener.
- [x] **Commands:** `/status`, `/margin`, `/scan`, `/help`, `/cleanup`.
- [x] **Safety:** Session-aware safety locks and 2-step confirmations.

## 📊 Phase 7: Automated Session Reporting (DONE ✅)
- [x] **Specification:** Reference `docs/REPORTING_SPECIFICATION.md`.
- [x] **Pre-Session Report:** Granular fund/collateral breakdown at market open.
- [x] **Post-Session Debrief:** P&L, Tax estimates, and T+1 margin at market close.
- [x] **Spot Parity:** 100% data alignment with Zerodha for daily changes.

---
*Last Updated: 2026-02-18 | Build: v3.5.0*
