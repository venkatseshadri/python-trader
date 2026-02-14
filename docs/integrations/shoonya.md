# 🔌 Shoonya API Integration

## Overview
ORBITER uses the **Finvasia Shoonya** API for all market data and order execution.

## Authentication
- **Endpoint**: `NorenApi.login()`
- **Credentials**: Stored in `ShoonyaApi-py/cred.yml`.
- **2FA**: The bot supports TOTP. If `factor2` is missing or invalid, it will prompt for interactive input on the CLI.

## Market Data (WebSocket)
We use a **Persistent WebSocket** connection.
- **Library**: `websocket-client` (via `NorenRestApiPy`).
- **Subscription**: We subscribe to `Touchline` (LTP, Open, High, Low) for all active symbols.
- **Handling**: Ticks are stored in `BrokerClient.SYMBOLDICT` for instant access by the Evaluator.

## Master Contracts
Shoonya provides daily CSV files with all active contracts.
- **Process**: On startup, `ScripMaster` downloads `NSE_symbols.txt.zip` and `NFO_symbols.txt.zip`.
- **Parsing**: The bot parses these to map `Token` (e.g., "26000") to `TradingSymbol` (e.g., "NIFTY26FEB...").
