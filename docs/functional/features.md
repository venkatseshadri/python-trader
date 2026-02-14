# ⚡ Functional Documentation

## 1. Dual-Mode Operation
ORBITER adapts its behavior based on the time of day.

| Mode | Time (IST) | Market | Instrument | Strategy |
| :--- | :--- | :--- | :--- | :--- |
| **Day** | 09:15 - 15:30 | **NFO** (Equity) | `OPTSTK` (Options) | **Credit Spreads** (Selling Premium) |
| **Evening** | 17:00 - 23:30 | **MCX** (Commodity) | `FUT` (Futures) | **Directional Momentum** |

## 2. Trading Strategy
The bot uses a "Score-based" system. It doesn't just look for one signal; it aggregates multiple factors.

### Entry Conditions
A trade is taken if **Total Score >= 60** (Configurable).
- **ORB (Opening Range Breakout)**: +30pts if price breaks the first 15-min high.
- **EMA Trend**: +10pts if Price > 5 EMA.
- **Supertrend**: +10pts if Supertrend is Green.

### Execution Logic
- **NFO**: If Bullish, it sells a **PUT Credit Spread** (Sell ATM PE, Buy OTM PE).
- **MCX**: If Bullish, it buys a **Future**.

## 3. Risk Management
The system employs a "Defense-in-Depth" approach.

### A. Trade-Level Exits
1.  **Stop Loss**: Hard exit if loss > 10% of premium.
2.  **Target**: Hard exit if profit > 10% of premium.
3.  **Trailing SL**:
    -   Starts once profit > 5%.
    -   Locks in profit as the trade moves in favor.

### B. Portfolio-Level "Kill Switch"
-   **Max Loss Limit**: If total daily loss exceeds `TOTAL_STOP_LOSS_RS` (e.g., ₹5000), **ALL** positions are squared off immediately and the bot stops entering new trades.
-   **Target Reached**: Similar logic for daily profit targets.
