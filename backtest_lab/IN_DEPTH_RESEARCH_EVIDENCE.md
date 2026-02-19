# 🧪 NIFTY 1% Mover: In-Depth Research Evidence (Feb 19, 2026)

This document provides the mathematical proof and in-depth analysis for the laws established in the Orbiter Strategy Foundation.

---

## 1. The Heartbeat Law: Volatility is the Default
We analyzed 105 NIFTY stocks over 2,700+ trading days to see how often they move >1% intraday.

### Data Proof (Sample Elite):
| Symbol | Total Days | Volatile Days (>1%) | **Heartbeat Frequency** |
| :--- | :--- | :--- | :--- |
| **ADANIENT** | 2,719 | 2,709 | **99.63%** |
| **JINDALSTEL** | 2,719 | 2,714 | **99.82%** |
| **BHEL** | 2,719 | 2,710 | **99.67%** |
| **NIFTY 50** | 2,735 | 1,173 | **42.89%** |

**Conclusion:** Individual stocks are 2x more likely to deliver a 1% move than the index. In the NIFTY 100, a 1% move is "market noise," not a breakout.

---

## 2. ORB-15 Capture Rate: The Front Door
We tested if the first 15 minutes of trading (09:15 - 09:30) could predict a 1% "Heartbeat" day.

### Data Proof (Capture Rate on 1% Days):
| Symbol | Heartbeat Days | ORB-15 Breaks | **Capture Rate %** |
| :--- | :--- | :--- | :--- |
| **NIFTY 50** | 1,173 | 1,171 | **99.83%** |
| **SBIN** | 2,579 | 2,558 | **99.19%** |
| **RELIANCE** | 2,502 | 2,478 | **99.04%** |
| **ABB** | 2,693 | 2,634 | **97.81%** |

**Conclusion:** The 15-minute ORB is a near-perfect gatekeeper. If a stock is going to have a volatile day, it breaks its ORB-15 window with **98.5% average probability**.

---

## 3. Launchpad Efficiency: Realizable Alpha
We measured the "ORB Eatup" (how much range is lost in the first 15 mins) vs. "Remaining Alpha" (profit potential after the break).

### Top 5 Launchpad Stocks:
| Symbol | Avg Total Range | ORB Eatup % | **Remaining Alpha %** |
| :--- | :--- | :--- | :--- |
| **NIFTY 50** | 1.63% | 33.00% | **67.00%** |
| **SBIN** | 2.68% | 41.84% | **58.16%** |
| **ADANIENT** | 4.41% | 42.46% | **57.54%** |
| **CANBK** | 3.87% | 42.75% | **57.25%** |
| **RELIANCE** | 2.23% | 45.35% | **54.65%** |

**Conclusion:** Large-cap banks and Indices are the most "efficient" for ORB trading because they preserve the most move for the post-break session.

---

## 4. The Gap & Reversal Paradox
Analysis of 458 high-gap events (>0.5%) to find the profit-booking "Sweet Spot."

### Key Discovery: The 1.5% Extension Rule
- **Mean Run after Gap:** 1.68% (B1) to 1.88% (B2).
- **Gap Negation Rate:** **25.8%** (Full reversal back to yesterday's close).
- **Reversal Correlation:** 0.261 (Large gaps lead to deeper intraday pullbacks).

**Conclusion:** On gap days, the "Safe Exit" is a **1.5% extension from the morning open**. Holding beyond this significantly increases the risk of being caught in the 25% of days that result in a total gap negation.

---

## 5. The Dynamic TP (Combined Budget)
We correlated ORB Size with the subsequent run to see if large ORBs "exhaust" the stock.

### Correlation Results:
- **Average Correlation:** **+0.242** (Positive).
- **Insight:** A large ORB does NOT exhaust the move; it often signals **Higher Intensity**, leading to a larger day.
- **Budgeting Rule:** `Target TP = (Historical_Budget - Current_ORB_Size) * 0.75`.
