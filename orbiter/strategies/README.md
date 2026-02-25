# 🧠 Trading Strategies (`orbiter/strategies/`)

## 🎯 Single Responsibility Principle (SRP)
The `strategies/` directory holds the **Execution Logic & Parameters** for various trading systems. Each sub-directory represents an independent, swappable algorithm that can be loaded dynamically via the CLI (`--strategyId=xyz`).

## 📂 Architecture
Each strategy folder (e.g., `nifty_fno_topn_trend/`, `mcx_trend_follower/`) must contain a consistent schema:

### 1. `strategy.json`
- The manifest file. Defines the `name`, `exchange_id`, `strategy_type`, and pointers to the supporting rule/filter files.
- Contains the `strategy_parameters` (e.g., `top_n: 5`, `trend_score_threshold: 0.5`) injected into the engine at runtime.

### 2. `rules.json`
- The compiled decision tree. Evaluates facts (like `session_is_trade_window`, `score > 0.5`) into distinct `Action` nodes (like `Buy_Top_N`).

### 3. `instruments.json`
- The universe definition. Specifies exactly which tokens or segments (e.g., NIFTY 50 Futures) the engine is allowed to monitor.

### 4. `filters.json`
- The specific technical guards and stop-loss trailing mechanics (e.g., EMA20 Trend Mortality, Premium Retracement buffers) attached to this specific algorithm.

## 🛑 Strict Boundaries
- Strategies are purely JSON configurations. No Python logic lives here.
- The `CoreEngine` is agnostic; it only behaves based on the active JSON structure loaded from this directory.