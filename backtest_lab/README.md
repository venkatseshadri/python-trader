# 🔬 Orbiter Backtest Lab v2.0

A high-performance research module for optimizing the ORBITER trading bot using historical NIFTY 50 1-minute data. Optimized for "Big Data" grid searches over 10+ years of history.

## 📂 Project Structure

- **`core/`**: The Simulation Engine.
  - `engine.py`: Row-by-row simulator for detailed P&L and Tradetron-style reports.
  - `mass_engine.py`: **Vectorized Numpy Matrix Engine** for 10-year simulations in < 1 second.
  - `loader.py`: Fast CSV loading with memory-efficient tail-reading.
  - `generator.py`: Logic for the **+6% / -1% weight-shift** grid generation.
- **`scenarios/`**: The Strategy Bank.
  - `master_suite/`: Library of **5,531 JSON scenarios** (All filter & weight permutations).
  - `all_weight_scenarios.csv`: Searchable catalog of every generated configuration.
- **`tools/`**: Development Utilities.
  - `generate_master_suite.py`: Re-generates the scenario library.
  - `csv_exporter.py`: Updates the summary CSV list.
- **`reports/`**: Visual HTML performance reports.

## 🧪 Optimization Methodology

### **The "Logical Weight" Model**
Instead of separate "on/off" flags, we treat **Weight = 0.0** as disabled. The suite explores every possible combination of filters (F1-F7), and for each combination, it performs a systematic shift.

### **Key Strategy Scenarios**

- **💎 Super-Alpha (Champion)**: The result of extensive grid-search optimization. Combines the core Trend logic (F2, F4) with explosive Momentum (F5, F6) and the F7 Volatility Shield.
  - *Metrics*: Profit Factor > 10.0, Win Rate ~66%, High ROI.
- **🚀 Alpha V2 + Shield**: A high-conviction momentum strategy using a surgical F7 filter to block trades during low-volatility "dead" markets.
- **🛡️ Triple Confirmation**: A "Sniper" style strategy (F2+F4+F7) that prioritizes trade quality over quantity. Very high profit factor but lower trade frequency.
- **🎯 Synergy Sweet Spot**: A balanced "Machine Gun" strategy (F2+F4) that maximizes trade volume while maintaining profitability.

### **Simulation Modes**
- **Detailed (Backtest Main)**: Used for single-scenario deep dives. Generates interactive Equity curves and Monthly heatmaps.
- **Mass (Batch Runner)**: Runs a folder of scenarios and ranks them in a leaderboard.
- **Ultra-Fast (Vector Runner)**: Uses Matrix multiplication to run the entire 19,000+ library over 10 years in seconds.

## 📊 Analytics Coverage

- **Equity Curve**: Net cumulative growth.
- **Profit Factor**: Gross Profit / Gross Loss (Primary quality metric).
- **Sharpe Ratio**: Risk-adjusted return calculation.
- **Win Rate**: Percentage of profitable trades.
- **Drawdown Plot**: Max risk and recovery duration.

## 🚀 Commands

### **1. Run 1-Year Optimization Suite**
```bash
python3 backtest_lab/batch_runner.py --csv [path_to_nifty_csv] --days 250
```

### **2. Run 10-Year Full History (Vectorized)**
```bash
python3 backtest_lab/vector_main.py --csv [path_to_nifty_csv] --days 2500
```

### **3. Review Scenarios in CSV**
Open `backtest_lab/scenarios/all_weight_scenarios.csv` in Excel to find a configuration you like, then run it specifically.
