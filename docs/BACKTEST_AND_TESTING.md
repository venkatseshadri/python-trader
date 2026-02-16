# 🧪 Testing & Research Documentation

This document covers the dual-layer testing infrastructure developed for the ORBITER trading framework.

---

## 1. Unit & Calibration Suite (`orbiter/tests/unit`)

Designed for technical accuracy and risk logic verification. These tests ensure the bot's math matches the real-world chart data.

### **Technical Analysis Calibration (`test_ta_utils.py`)**
- **Purpose**: Verifies EMA, SuperTrend, and ATR against "Golden Values" provided from a manual chart.
- **Precision**: Achieves 0.00 drift using TA-Lib Metastock compatibility.
- **Data Source**: `nifty_ta_chunk.csv` (2025-07-21).

### **Risk Management Logic (`test_sl_tp_logic.py`)**
- **Trailing SL**: Verifies the 5% activation and X% retracement logic.
- **Portfolio Mass Exit**: Ensures all positions close when the aggregate P&L hits the target/SL.
- **Individual Filters**: Tests specific exit triggers like "Below ORB Low."

### **Scenario Stress Tests (`test_reversal_logic.py`)**
- **Crash Simulation**: Replays the 12:27-12:30 PM "Flash Dip" from July 21st.
- **Convergence**: Proves that the combined signal of F1-F6 stack forces an exit before the crash.

---

## 2. Backtest Lab (`backtest_lab/`)

A high-performance research module for long-term strategy optimization.

### **Key Components**
- **`core/mass_engine.py`**: A fully vectorized Numpy engine that can simulate 10 years of data in < 1 second.
- **`core/generator.py`**: Automates the creation of thousands of JSON scenarios based on filter combinations and weight shifts.
## 🛡️ Orbitron Professional Backtesting Utility

The Orbitron utility is designed for high-fidelity strategy verification, producing Tradetron-replica PDF reports and detailed transaction ledgers.

### Core Features
- **Multi-TF Analysis**: Native support for 1m, 5m, and 15m data synchronization.
- **Institutional Sniper Strategy**: Built-in strategy utilizing EMA crossovers, ADX strength, and ORB (Opening Range Breakout) filters.
- **High-Fidelity PDF (Orbitron Report)**:
    - Shaded Equity and Drawdown curves.
    - Automatic identification of Max Drawdown recovery periods.
    - Monthly PNL Heatmaps and Returns Histograms.
    - Full-year daily PNL calendars.
- **Excel Ledger**: Complete trade-by-trade breakdown for tax and logic audits.

### Usage
Run a professional backtest using the specialized CLI tool:
```bash
./.venv/bin/python3 backtest_lab/tools/backtest_cli.py \
    --stocks RELIANCE TCS HDFCBANK \
    --start 2025-01-01 \
    --end 2025-12-31 \
    --output backtest_lab/reports/my_study
```

### Reporting Engine
- **`core/pdf_generator.py`**: Handles the visual layout, branding, and chart generation.
- **`core/reporter.py`**: Calculates advanced risk metrics (Sharpe, Volatility, Max Drawdown).
- **`core/loader.py`**: Optimized candle loading with indicator pre-calculation.

### **Running Simulations**
- **Batch Run**: `python3 backtest_lab/batch_runner.py --days 250` (Runs scenarios in the `scenarios/` folder).
- **Vector Run**: `python3 backtest_lab/vector_main.py --days 2500` (Fastest run for long history).
- **Optimization Suites**: Specialized runners for `risk_optimizer.py`, `weight_optimizer.py`, and `golden_stack_tuner.py`.

---

## 3. Best Practices for Strategy Refactoring

1. **Parameterization**: Never hardcode values. Use the JSON scenario files in `backtest_lab/scenarios/`.
2. **Regression Testing**: After changing a filter's code, run `pytest tests/unit/test_ta_utils.py` to ensure the "Golden Values" still match.
3. **The "Truth Run"**: Always verify a new strategy idea over at least 1 year using the `vector_main.py` before going live.
