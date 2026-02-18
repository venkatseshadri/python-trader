# 📋 Technical Plan: Session-Based Summary System

## 🎯 Objective
Provide the user with high-fidelity financial and operational snapshots via Telegram at the exact start and end of each trading session (NFO/MCX).

## 🏗️ Architecture

### 1. Data Acquisition (Broker Layer)
- **Tool:** `BrokerClient` (extending `ShoonyaApiPy`).
- **Required Endpoints:**
    - `get_limits()`: Detailed breakdown of Cash, Margin Used, Collateral, and Pay-in.
    - `get_positions()`: Live P&L, Net Quantity, and Buy/Sell averages.
    - `get_order_book()`: Full session activity to calculate slippage and order counts.

### 2. Analytics Engine (`SummaryManager`)
- **Financial Module:**
    - **Gross P&L:** Sum of Realized + Unrealized.
    - **Net P&L:** Gross P&L minus (Brokerage + STT + Exchange Charges + GST).
    - **T+1 Estimation:** `Net P&L - (Brokerage * 0.18 GST) + Pending Settlements`.
- **Portfolio Module:**
    - **Exposure:** Total value of open positions.
    - **Concentration:** Highlight if any single symbol exceeds 40% of utilized margin.
    - **Slippage:** `(Executed Price - Signal Price) / Signal Price * 100`.

### 3. Lifecycle Management (`main.py`)
- **Trigger A (Pre-Session):** 9:30 AM (NFO) / 5:30 PM (MCX).
- **Trigger B (Post-Session):** 3:35 PM (NFO) / 11:35 PM (MCX).
- **State Check:** Ensure reports are sent exactly once per transition using a session-specific UUID or timestamp.

## 🕒 Estimated Timeline
| Task | Description | Time |
| :--- | :--- | :--- |
| **Step 1** | Enhance `BrokerClient` for granular margin data. | 45m |
| **Step 2** | Build `TaxCalculator` (Brokerage/STT logic). | 60m |
| **Step 3** | Implement T+1 Margin & Portfolio analytics. | 60m |
| **Step 4** | Telegram Template Design (Rich Formatting). | 30m |
| **Step 5** | Integration & End-to-End Testing. | 45m |
| **TOTAL** | | **~4.0 Hours** |

## 📝 Implementation Notes
- **Tax Proxy:** For Option Spreads, assume ₹40/spread (2 legs) + 0.1% of premium value for STT/Charges.
- **T+1 Logic:** Profits are usually credited to margin on T+1 morning. Loss is deducted instantly.
