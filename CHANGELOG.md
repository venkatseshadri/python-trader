# Changelog

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
