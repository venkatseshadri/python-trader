# ORBITER & SNIPER: Production Roadmap

## 🤖 Phase 1: Remote Monitoring & Alerts (DONE ✅)
- [x] **Telegram Integration:** 
    - [x] **Remote Error Watcher:** Tail system logs on RPi and ping Telegram for CRITICAL/ERROR status.
    - [x] **Trade Alerts:** Send real-time execution notifications to your private channel.
    - [x] **Heartbeat Pings:** Daily check-in at market open to confirm the bot is alive.
- [x] **Emergency Kill-Switch:** Handled via RPi shell access / upcoming Telegram commands.
- [x] **Session Lifecycle:** Implemented Hibernation/Smart Rest to stop restart loops.

## 🔬 Phase 2: Filter Reverse Engineering (IN PROGRESS ⏳)
- [ ] **Mass Attribute Analysis:** Expand the ATGL 35-property study to the entire `orbiter_revamp_data.csv` dataset.
    - [ ] **Batch Processing:** (Batch 0 Running...) Run analysis in 5 batches of ~21 stocks each.
    - [ ] **Consolidation:** Merge `batch_0.csv` through `batch_4.csv` into a master `orbiter_revamp_data.csv`.
- [ ] **Correlation Matrix:** Identify which indicators (ADX, RSI, EMA Slopes, ATR) have the highest "Predictive Power" for 1% moves.
- [ ] **Filter Pruning:** Eliminate "Noise Filters" that don't add value.
- [ ] **Threshold Tuning:** Determine the "Sweet Spot" values (e.g., ADX > 25 vs ADX > 30).
- [ ] **Attribution Report:** Generate a final HTML report showing which filter combinations led to the highest Win Rate vs. Drawdown.

## ✅ Phase 2: Validation & Cohesion
- [ ] **Out-of-Sample Testing:** Run the new filter stack on 2024 data (unseen data) to prevent "overfitting."
- [ ] **Strategy Cohesion:** Verify that "Trend Following" filters don't get neutralized by "Mean Reversion" filters in the same stack.
- [ ] **Slippage Simulation:** Add 0.05% - 0.1% artificial slippage to backtests.

## 📉 Phase 3: Backtest (SNIPER) Refinement
- [ ] **Orbitron Shaded Graph:** Fix the Drawdown visualization in PDF/HTML reports (Revisit shaded area logic).
- [ ] **Vectorization Check:** Compare results between `vector_main.py` and `engine.py` to ensure 100% parity.
- [ ] **Equity Curve Smoothing:** Optimize position sizing logic based on new filter conviction levels.

## 🤖 Phase 4: Remote Monitoring (ORBITER)
- [ ] **Live Transition:** Switch from `--simulation` to `Live Mode` (NFO/MCX).
- [ ] **Emergency Kill-Switch:** Implement a remote command (file-trigger or API) to close all positions instantly.
- [ ] **Telegram Integration:** 
    - [ ] **Remote Error Watcher:** Tail system logs on RPi and ping Telegram for CRITICAL/ERROR status.
    - [ ] **Trade Alerts:** Send real-time execution notifications to the private channel.
    - [ ] **Heartbeat Pings:** Daily check-in at market open to confirm the bot is alive.
- [ ] **Session Lifecycle:** Finalize auto-exit at 15:25 (NFO) and 23:25 (MCX) for clean daemon restarts.

## 🛠️ Phase 5: DevOps & Integrity
- [ ] **Portable Checksums:** Update `release.sh` to use relative-path SHA-256 hashes.
- [ ] **Automated Updates:** Verify the `update.sh` loop over Tailscale without manual password entry.
- [ ] **Log Rotation:** Implement log rotation to prevent SD card overflow on Pi.

---
*Last Updated: 2026-02-17*
