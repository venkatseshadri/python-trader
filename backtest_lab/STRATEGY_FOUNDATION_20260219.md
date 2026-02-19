# 🛡️ Orbiter Strategy Foundation (Feb 19, 2026)

## 1. The Heartbeat Law
- **Finding:** 95% of NIFTY 100 stocks move >1% intraday on >95% of days.
- **Action:** Stop using "1% move" as a success metric. Use **"Alpha Expansion"** (moves beyond 1.5% or 2%) to find real institutional trends.

## 2. ORB-15 Reliability
- **Finding:** 15-minute ORB breaks have a **98.5% correlation** with 1% heartbeat days.
- **Action:** The 15-min ORB is the mandatory "Front Door" for all entries. No break = No trade.

## 3. The Launchpad Stocks
- **Finding:** PSU Banks (SBIN, CANBK) and Adani stocks (ADANIENT) preserve the most profit potential *after* the ORB break.
- **Top Pick:** **ADANIENT** (Avg 4.4% range, 57% Alpha remaining post-ORB).

## 4. The Gap-Exhaustion Paradox
- **Finding:** Large gaps do NOT stop a trend, but they **trigger violent reversals.**
- **Finding:** 25.8% of high-gap days (>0.5%) result in a **Total Gap Negation** (Full reversal).
- **The 1.5% Rule:** Profit booking consistently occurs after a 1.5% extension from the morning open on gap days.

## 6. The Dynamic TP (Total Budget) Law
- **The Concept:** Every stock has a "Total Intraday Budget" = `ORB-15 Size` + `Post-Break Run`.
- **Finding:** While a large ORB doesn't *stop* a move, the "Combined Budget" is mathematically stable for each stock (e.g., 4.1% for ADANIENT, 2.2% for RELIANCE).
- **The Filter Logic:** 
    *   `Remaining_Alpha = (Historical_Total_Budget - Current_ORB_Size)`
    *   `Dynamic_TP = Remaining_Alpha * 0.75` (Targeting 75% of the remaining expected move).
- **Strategic Value:** This prevents the bot from holding a trade for a 0.75% gain on a day where the ORB already consumed 1.0% of a 1.5% budget.

## 5. Optimized Filter Configuration (v3.9.0+)
- **Entry Score:** 10.0 (High Conviction only).
- **Exit Strategy:** 0.5% Hard SL + 1m EMA20 Trend Exit + 3-Candle Wick Reversal Detection.
- **Timing:** Primary execution window 10:15 - 13:00 IST.
