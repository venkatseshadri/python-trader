# NFO Trading Flow - Architecture Diagram

## Flow Overview

```mermaid
flowchart TD
    A[START: Strategy Run] --> B[Load instruments.json]
    B --> C[For each stock symbol]
    C --> D[Get futures data]
    
    D --> E{futures_master.json exists?}
    E -->|Yes| F[Load futures from file]
    E -->|No| G[Error: No futures data]
    G --> H[END - Skip stock]
    
    F --> I[Calculate indicators<br/>ADX, EMA, SuperTrend]
    I --> J[Score calculation<br/>from rules.json]
    J --> K{Score >= Threshold?}
    
    K -->|No| C
    K -->|Yes| L[TRADE: Place Options Order]
    
    L --> M[resolve_option_symbol<br/>symbol, ltp, option_type<br/>strike_logic, expiry_type]
    M --> N[_select_expiry<br/>determine expiry date]
    N --> O[_get_option_rows<br/>symbol, ltp, expiry<br/>instrument]
    
    O --> P{Local file has<br/>option data?}
    P -->|Yes| Q[Return rows from file]
    P -->|No| R[Query broker API<br/>get_security_info]
    
    R --> S[Get lot_size from<br/>broker API]
    S --> T[Generate strikes<br/>around ATM (ltp)]
    T --> U[Return option rows<br/>with lot_size]
    Q --> U
    
    U --> V[Apply strike_logic<br/>ATM, ATM+1, ATM-4]
    V --> W[Return contract details<br/>token, tradingsymbol<br/>lot_size, exchange]
    W --> X[place_spread<br/>Execute order]
    X --> Y[END]
```

## Data Sources

| Phase | Data | Source |
|-------|------|--------|
| Scanning | Futures | `futures_master.json` ✅ EXISTS |
| Trading | Options | Broker API (on-the-fly) |

## Key Files

```
orbiter/
├── strategies/nifty_fno_topn_trend/
│   ├── instruments.json     # Stock symbols to trade
│   ├── rules.json           # Scoring rules, strike_logic
│   └── filters.json         # Filter weights
├── data/
│   ├── futures_master.json   # ✅ Futures data (exists)
│   └── options_master.json  # ❌ Options data (NOT NEEDED)
└── core/broker/
    └── resolver.py          # Option resolution logic
```

## Method Flow

```
1. Strategy.run()
   │
   ├── instruments.json → Get stock symbols
   │
   ├── For each symbol:
   │   ├── Get futures from futures_master.json
   │   ├── Calculate indicators (ADX, EMA, SuperTrend)
   │   ├── Calculate score from rules.json
   │   └── If score >= threshold → TRADE
   │
   └── Trade execution:
       ├── resolve_option_symbol(symbol, ltp, 'CE', 'ATM+1', 'weekly')
       │   ├── _select_expiry(symbol, 'weekly', 'OPTSTK')
       │   │   └── Determine expiry from futures_master.json
       │   │
       │   └── _get_option_rows(symbol, ltp, expiry, 'OPTSTK')
       │       ├── Try futures_master.json
       │       │   └── If empty → Query broker API
       │       │       ├── get_security_info(exchange, token) → lot_size
       │       │       └── Generate strikes around ATM (ltp)
       │       │
       │       └── Apply strike_logic: ATM → ATM+1
       │
       └── place_spread() → Broker API order
```

## JSON Configuration Examples

### instruments.json
```json
[
  {"symbol": "RELIANCE", "exchange": "NSE", "derivative": "option", "instrument_type": "stock"},
  {"symbol": "TCS", "exchange": "NSE", "derivative": "option", "instrument_type": "stock"}
]
```

### rules.json (strike_logic from JSON)
```json
{
  "order_operations": [
    {"type": "trade.place_spread", "params": {"side": "BUY", "strike": "ATM+1", "option_type": "CE"}},
    {"type": "trade.place_spread", "params": {"side": "SELL", "strike": "ATM-1", "option_type": "PE"}}
  ]
}
```

## Decision Points

| Decision | Logic |
|----------|-------|
| Use local file? | If `futures_master.json` has data → use it |
| Use broker API? | Only if local file is empty for OPTIONS |
| Generate strikes? | Around LTP (10 above, 10 below) |
| lot_size? | From broker API `get_security_info` |
