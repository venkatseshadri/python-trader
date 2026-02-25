# 📊 Analytics & Reporting (`orbiter/core/analytics/`)

## 🎯 Single Responsibility Principle (SRP)
The `analytics/` directory isolates all **Financial Calculations and Trade Reporting**. It transforms raw trade data (prices, quantities, segment identifiers) into human-readable metrics (PnL, Margin, ROI, Taxes).

## 📂 Architecture

### 1. `summary.py` (SummaryManager)
- **Responsibility:** The centralized hub for performance tracking.
- Tracks `peak_pnl`, `realized_pnl`, and `unrealized_pnl` across the entire portfolio.
- Integrates segment-specific tax and brokerage calculators to estimate Net PnL accurately.
- Consumes real-time margin queries to provide "Available Liquidity" context to the broader system.

### 2. Tax & Brokerage Handlers
- Ensures high-fidelity reporting by separating NFO (Options/Futures) transaction charges from MCX (Commodities) calculations, which vary significantly.

## 🛑 Strict Boundaries
- No trading decisions are made here. The engine might query this module to determine if a "Global Trailing SL" should be triggered, but the analytics module itself only *calculates*, it never *executes*.