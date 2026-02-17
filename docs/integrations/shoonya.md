# 🔌 Shoonya API Integration

## Overview
ORBITER uses the **Finvasia Shoonya** API for all market data and order execution.

## Authentication
- **Endpoint**: `NorenApi.login()`
- **Credentials**: Stored in `ShoonyaApi-py/cred.yml`.
- **2FA**: The bot supports manual `factor2` input and **Automated TOTP**.

### Automated 2FA (Recommended for Service)
To allow the bot to run as a background service without prompting for a 2FA code, add your TOTP secret key to `cred.yml`:

```yaml
user: YOUR_USER_ID
pwd: YOUR_PASSWORD
vc: YOUR_VENDOR_CODE
apikey: YOUR_API_KEY
imei: YOUR_IMEI
totp_key: "YOUR_TOTP_SECRET_HERE"  # Add this line
```

The bot will use the `pyotp` library to generate a fresh code every time it starts or restarts.

## Market Data (WebSocket)
We use a **Persistent WebSocket** connection.
- **Library**: `websocket-client` (via `NorenRestApiPy`).
- **Subscription**: We subscribe to `Touchline` (LTP, Open, High, Low) for all active symbols.
- **Handling**: Ticks are stored in `BrokerClient.SYMBOLDICT` for instant access by the Evaluator.

## Master Contracts
Shoonya provides daily CSV files with all active contracts.
- **Process**: On startup, `ScripMaster` downloads `NSE_symbols.txt.zip` and `NFO_symbols.txt.zip`.
- **Parsing**: The bot parses these to map `Token` (e.g., "26000") to `TradingSymbol` (e.g., "NIFTY26FEB...").
