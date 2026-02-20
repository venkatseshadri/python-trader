# ORBITER & SNIPER: Production Roadmap

## 🤖 Phase 1: Infrastructure & Basic Monitoring (DONE ✅)
- [x] **Telegram Integration:** Heartbeat, Alerts, and Error Watcher.
- [x] **Emergency Kill-Switch:** Manual RPi shell access.
- [x] **Session Lifecycle:** Hibernation/Smart Rest logic.
- [x] **Persistence:** Restart-proof state management via `session_state.json`.
- [x] **MCX Integration:** Full futures mapping and lot size resolution.

## 🔬 Phase 2: Filter Reverse Engineering (IN PROGRESS ⏳)
- [x] **Initial Study:** Completed 35-property analysis for ATGL.
- [x] **Research Laws 1-3:** Implemented Dynamic TP, 15m EMA20 SL, and Alpha weighting.
- [x] **Score Velocity:** Real-time momentum trend tracking (Morning vs Now).
- [ ] **Mass Attribute Analysis:** Study entire `orbiter_revamp_data.csv` in batches.
- [ ] **Correlation Matrix:** Identify highest "Predictive Power" indicators.
- [ ] **Filter Pruning:** Eliminate low-value noise filters.

## 📊 Phase 3: Validation & Sniper Refinement
- [ ] **Out-of-Sample Testing:** 2024 backtest validation.
- [x] **Orbitron Shaded Graph:** Fix drawdown visualization logic. (Completed during core stability fixes)
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

## 🛡️ Phase 8: Quality & Reliability (DONE ✅)
- [x] **Mandatory Pre-Release Tests:** Integrated `run_tests.sh` into `release.sh`.
- [x] **Coverage Baseline:** Established at 48% for Orbiter Core.
- [x] **Coverage Milestone: Bulletproof Core**
    - [x] 🎯 **Level 1:** Reached **60%** Coverage (Resolver & Margin logic)
    - [x] 🎯 **Level 2:** Reached **70%** Coverage (Connection & Analytics)
    - [ ] 🎯 **Level 3:** Reach **80%** Coverage (Advanced Edge Cases)
    - [ ] 🎯 **Level 4:** Reach **90%+** Coverage (Mission Critical)
    - [ ] 🏁 **Level 5:** Reach **100%** Coverage (Total Verification)

---
*Last Updated: 2026-02-20 | Build: v3.9.6 (STABLE)*
