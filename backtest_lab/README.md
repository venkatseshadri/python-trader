# 🛡️ Backtest Lab

The central hub for strategy development, optimization, and high-fidelity reporting.

## 🚀 Primary Tools

### `tools/backtest_cli.py`
**The Gold Standard.** Use this for all standard backtesting. It integrates multi-timeframe data (1m, 5m, 15m) and generates the "Orbitron" High-Fidelity PDF report.
- **Features**: Institutional Sniper logic, Trailing SL, 70% Profit Retention, and Tradetron-replica PDF output.
- **Usage**: `python tools/backtest_cli.py --stocks RELIANCE --start 2025-01-01 --end 2025-12-31`

### `runners/batch_runner.py`
Automates the execution of `backtest_cli` across multiple stock lists or date ranges defined in the script. Ideal for overnight runs.

### `runners/vector_main.py`
A high-performance, vectorized implementation of backtesting logic using NumPy. Used for rapid research and preliminary strategy screening where per-candle loops are too slow.

### `runners/mass_optimizer_run.py`
A wrapper script designed to manage long-running optimization jobs, providing progress logging and crash recovery.

---

## 📈 Optimization Suite (`optimization/`)

### `optimization/mega_stock_optimizer.py`
Iterates through hundreds of stocks and parameter combinations to find the "Sweet Spot" for the current market regime. Results are often saved to `mega_optimization_results.csv`.

### `optimization/risk_optimizer.py`
Focuses on the survival aspect. It takes a baseline strategy and iterates through Stop-Loss and Take-Profit (SL/TP) configurations to maximize the Sharpe Ratio and minimize Drawdown.

### `optimization/weight_optimizer.py`
Determines the optimal capital allocation across a basket of stocks. It uses equity curve correlation to ensure the portfolio is not overly exposed to a single sector or move.

---

## 🏗️ Core Architecture (`core/`)

- **`engine.py`**: The underlying simulation logic.
- **`loader.py`**: Optimized data loading and technical indicator (TA-Lib) injection.
- **`pdf_generator.py`**: The "Orbitron" reporting engine (ReportLab/FPDF + Seaborn).
- **`reporter.py`**: Mathematical library for calculating advanced risk metrics like Drawdown recovery days and Rolling Sharpe.
- **`excel_generator.py`**: Generates the transaction ledger for audit purposes.

---

## 🧪 Validation (`tests/`)

- **`tests/test_suites.py`**: Developer-focused tests to ensure engine logic remains consistent during updates.

---

## 📁 Workspace Structure

- **`data/stocks/`**: Local CSV repository for minute-level OHLCV data.
- **`scenarios/`**: JSON configuration files for strategy parameters.
- **`reports/`**: Output directory for PDFs and Excel files (Cleaned regularly).
- **`archives/`**: Legacy scripts, one-off studies, and deprecated report generators.
