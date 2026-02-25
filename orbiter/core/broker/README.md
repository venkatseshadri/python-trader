# 🔌 Broker Integration (`orbiter/core/broker/`)

## 🎯 Single Responsibility Principle (SRP)
The `broker/` directory acts as the **Anti-Corruption Layer (ACL)** between the external trading API (Shoonya) and Orbiter's internal `CoreEngine`. It translates proprietary API responses into generic internal data structures and translates internal trading intents into API-specific order requests.

## 📂 Architecture

### 1. `__init__.py` (BrokerClient)
- The main singleton facade exposing simple, high-level methods like `login()`, `start_live_feed()`, and `place_order()`.
- Manages the live `SYMBOLDICT` populated by the websocket.

### 2. `connection.py`
- Handles the actual authentication, websocket lifecycle, and network resiliency (auto-reconnects).

### 3. `executor.py`
- Formats and dispatches actual HTTP order payloads to the exchange. Ensures correct formatting for Limit, Market, and SL orders.

### 4. `resolver.py`
- Translates human-readable symbols (e.g., "NIFTY", "RECLTD") into Exchange Tokens (e.g., "NFO|12345") required by the API.

### 5. `margin.py`
- Fetches and parses account balances and margin limits.

### 6. `master/` (Scrip Masters)
- **Responsibility:** Downloading and caching the official exchange Scrip Masters (CSV files) locally to ensure lightning-fast token resolution.
- Separated into `equity.py`, `futures.py`, and `options.py` to handle the unique data shapes of different instruments.

## 🛑 Strict Boundaries
- No strategy logic exists here. The broker blindly executes what it is told.
- The deprecated `core/client.py` has been fully dismantled into this modular structure. Do not use it.