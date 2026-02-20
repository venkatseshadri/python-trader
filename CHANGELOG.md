# Changelog

## [3.10.0-20260220-954f8fc] - 2026-02-20
### Changed
- Automated release update using original versioning scheme.

## [3.10.0] - 2026-02-20
### Strategic Overhaul & Production Hardening
- **Smart ATR SL:** Replaced fixed 10% premium stops with dynamic, volatility-adjusted buffers (1.5x ATR for Futures, 0.25x ATR for Spreads).
- **Automatic Priming:** Implemented a Fast-Start mechanism that proactively fetches historical candles on startup, eliminating the "15-minute wait" for technical guards.
- **Segment-Strict Resolution:** Fixed the "NFO Master Leak" where MCX sessions were stalled by massive NFO downloads. Isolated resolution ensures 99% faster scrip refreshes.
- **Crash Protection:** Hardened the execution loop with `try-except` wrappers and strict data validation to prevent single-symbol data errors from killing the bot.
- **Repository Deep Clean:** Surgically purged 2.4GB of historical bloat (old venvs, huge data dumps) from Git history, shrinking the repository to 26MB.

## [3.9.6] - 2026-02-20
### Added
- **Research Strategy Laws 1-3:** Implemented Dynamic TP (`(Budget - ORB) * 0.75`), 15m EMA20 "Trend Mortality" SL, and Research-based Alpha Weighting.
- **Session Persistence:** Added `session_state.json` to preserve active positions and exit history across restarts (with 30-min freshness protocol).
- **Forensic Data Layer:** Enhanced position logs to include both underlying LTP and raw option premium components (ATM/Hedge/Net).
- **Entry Guards:** Implemented Slope Guard (EMA5) and Freshness Guard (Price near High) to stop re-entry churn.

### Fixed
- **Simulation Bug:** Fixed missing `ok: True` key in simulated future/spread order returns.
- **Dependency Fix:** Switched to `talib` for EMA20 calculation to resolve `ModuleNotFoundError` on Raspberry Pi.
- **Date Parsing:** Made date resampling robust to both DD-MM-YYYY and YYYY-MM-DD formats.
- **Notification Storm:** Consolidated SL/TP alerts into a single Telegram message with full PnL details.

### Security
- **Memory Workflow:** Hardcoded mandatory documentation updates into the development workflow.
