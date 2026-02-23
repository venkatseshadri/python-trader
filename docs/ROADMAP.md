# ORBITER & SNIPER: Production Roadmap

## 🤖 Phase 1: Infrastructure & Basic Monitoring (DONE ✅)
- [x] **Telegram Integration:** Heartbeat, Alerts, and Error Watcher.
- [x] **Emergency Kill-Switch:** Manual RPi shell access.
- [x] **Session Lifecycle:** Hibernation/Smart Rest logic.
- [x] **Persistence:** Restart-proof state management via `session_state.json`.
- [x] **UX Refactor (P1):** Consolidated batch entry alerts and suppressed margin spam.
- [x] **Segment Isolation:** Prevent cross-segment master stalls (MCX vs NFO).
- [x] **Automatic Priming:** Fast-start candle pre-filling (eliminates 15m blind spot).
- [x] **MCX Integration:** Full futures mapping and lot size resolution.

## 🔬 Phase 2: Filter Reverse Engineering (DONE ✅)
- [x] **Initial Study:** Completed 35-property analysis for ATGL.
- [x] **Research Laws 1-3:** Implemented Dynamic TP, 15m EMA20 SL, and Alpha weighting.
- [x] **Score Velocity:** Real-time momentum trend tracking (Morning vs Now).
- [x] **Smart SL V2:** Underlying-aware risk (Stock % + Cash PnL ₹).
- [x] **Smart ATR SL:** Volatility-adjusted dynamic stop loss (ATR-based).
- [x] **Relative Freshness:** Dynamic breakout window (15m) for multi-session stability.
- [ ] **Mass Attribute Analysis:** Study entire `orbiter_revamp_data.csv` in batches. (Next Milestone)
- [ ] **Correlation Matrix:** Identify highest "Predictive Power" indicators.
- [ ] **Filter Pruning:** Eliminate low-value noise filters.

## 📊 Phase 3: Validation & Sniper Refinement
- [ ] **Out-of-Sample Testing:** 2024 backtest validation.
- [x] **Orbitron Shaded Graph:** Fix drawdown visualization logic. (Completed during core stability fixes)
- [ ] **Vectorization Check:** Parity check between vector vs loop engines.

## 🚀 Phase 4: Live Transition & Scaling
- [x] **Session Target Management:** Implemented hard stops (`TOTAL_TARGET_PROFIT_RS=5000`) and early trailing (`TSL_ACTIVATION_RS=500`) to secure wins. (2026-02-23)
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
- [x] **Confidence Coverage:** Shifted focus from vanity metrics to failure-mode testing.
- [x] **Persistence Unit Tests:** Regression tests for JSON serialization and corruption recovery.
- [x] **Coverage Milestone: Bulletproof Core**
    - [x] 🎯 **Level 1:** Reached **60%** Coverage (Resolver & Margin logic)
    - [x] 🎯 **Level 2:** Reached **70%** Coverage (Connection & Analytics)
    - [x] 🎯 **Level 3:** Reached **80%** State Coverage (Persistence Layer)
    - [ ] 🎯 **Level 4:** Reach **90%+** Coverage (Mission Critical)
    - [ ] 🏁 **Level 5:** Reach **100%** Coverage (Total Verification)

---
*Last Updated: 2026-02-23 | Build: v3.11.0 (STABLE)*