# Take Profit (TP) Filters

This folder contains the logic for managing winning trades. The system uses a "Defense-in-Depth" approach with three distinct filters that operate on different mathematical principles to lock in gains and protect against reversals.

## 1. Fixed Target (`tf1_premium_decay_10`)
*   **Purpose**: The "Hard Exit" goal.
*   **Trigger**: Profit hits exactly **10%** of the Short Premium (ATM).
*   **Logic**: If you sold an option for ₹100 and its value decays to ₹90, the bot exits immediately.
*   **Role**: This is the primary profit objective for every trade.

## 2. Tightening Floor (`tf2_trailing_sl`)
*   **Purpose**: Protects a "good" trade from turning into a loss using percentage-based trailing.
*   **Activation**: Automatically activates once the trade reaches **5% profit**.
*   **Logic**: `Trailed SL % = Current Max Profit % - 5%`.
    *   At **5% profit**: Trailed SL is set to **0% (Break-even)**.
    *   At **8% profit**: Trailed SL is set to **3% locked-in profit**.
*   **Role**: Ensures that as the trade approaches the 10% goal, the safety floor rises proportionally.

## 3. Drawdown Shield (`tf3_retracement_sl`)
*   **Purpose**: Protects against sharp reversals in **Cash (Rupee) terms**.
*   **Activation**: Activates once the trade has achieved at least **₹1000 profit** (configurable via `TSL_ACTIVATION_RS`).
*   **Logic**: Exits if the current profit drops by **50%** (configurable via `TSL_RETREACEMENT_PCT`) from the peak cash PnL.
    *   If peak profit was **₹2000**, the safety net is at **₹1000**.
*   **Role**: Specifically designed for volatile stocks where percentage moves might look stable, but the actual cash swing is significant.

---

## How They Work Together
The filters work in a hierarchy. During every market scan, the bot evaluates all active filters. **Whichever floor or target is hit first triggers an immediate square-off.**

### Example Lifecycle (Trade with ₹2000 potential profit):
1.  **Early Stage (0% to 4.9% profit)**: No TP filters are active. Only the Stop Loss (-10%) is protecting the capital.
2.  **Momentum Stage (5% profit / ₹1000)**: Both `tf2` and `tf3` activate.
3.  **Advanced Stage (8% profit / ₹1600)**:
    *   `tf2` floor is at **3% profit**.
    *   `tf3` floor is at **₹800** (50% of ₹1600).
4.  **Goal Stage (10% profit / ₹2000)**: `tf1` triggers and the trade is closed with full profit.
