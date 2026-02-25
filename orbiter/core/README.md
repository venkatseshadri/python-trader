# 🧠 Core Application Layer (`orbiter/core/`)

## 🎯 Single Responsibility Principle (SRP)
The `core/` directory is responsible exclusively for the **Domain Logic** of the trading system. It orchestrates the flow of data between the external broker (`broker/`), the decision-making engine (`engine/`), and the performance tracking module (`analytics/`).

## 📂 Sub-Modules

### 1. `app.py` (The Conductor)
- **Responsibility:** Binds the `SessionManager`, `RuleManager`, `ActionManager`, and `RegistrationManager` together.
- It is the master loop (`run()`) that continuously polls the rules engine and executes batched actions.
- Manages high-level system states: initialized, logged_in, primed.
- Hosts the background thread for pushing performance metrics to Google Sheets.

### 2. `broker/` (The External Interface)
- **Responsibility:** Abstracting all communication with the physical trading API (Shoonya).

### 3. `engine/` (The Brain)
- **Responsibility:** Evaluating strategy rules against live data, determining actions (Buy, Sell, Trailing SL), and maintaining the real-time state of the portfolio.

### 4. `analytics/` (The Accountant)
- **Responsibility:** Calculating metrics, PnL, margin availability, and taxes.

## 🛑 Strict Boundaries
- `core/` does **not** handle user inputs or Telegram messages directly. It receives facts from `utils/` and triggers actions that `bot/` might listen to.
- `core/` does **not** define strategies. It dynamically loads them via the `SessionManager`.