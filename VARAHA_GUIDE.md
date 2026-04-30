# 🐗 Varaha - NFO/BFO Index Trading Bot

**Varaha** is an automated NSE index trading bot that trades during regular market hours (9:20 AM - 3:30 PM IST) on NIFTY and SENSEX index futures/options (NFO/BFO), releasing margin for Kurma's evening commodities trading.

**Mission:** Generate ₹3,000-₹5,000 daily profit using systematic trend-following strategies, with capital preservation as the primary objective.

---

## 📊 Trading Scope

### Markets
| Market | Instruments | Hours | Usage |
|--------|-------------|-------|-------|
| **NFO** | NIFTY futures, options | 9:20 AM - 3:30 PM | Primary - high liquidity |
| **BFO** | SENSEX futures, options | 9:20 AM - 3:30 PM | Secondary - larger ticks |
| **Equity** | Yes (NSE) | 9:15 AM - 3:30 PM | Secondary |

### Capital Flow
```
9:20 AM:  Varaha locks ₹4,00,000 margin from account
3:05 PM:  Varaha exits ALL positions (closes out completely)
3:10 PM:  Margin released back to account
5:20 PM:  Kurma receives same ₹4,00,000 for evening trading
11:20 PM: Kurma exits all positions
NEXT DAY: Full cycle repeats
```

**Key Rule:** Varaha MUST exit completely by 3:05 PM to free margin for Kurma. No overnight positions.

---

## 🏗️ Architecture

### System Components

```
varaha_main.py            Master orchestrator (market hours, phase control)
├── varaha_sentinel.py    Real-time monitoring, 1-second quote updates
├── varaha_master.py      Historical data fetch, instrument discovery
├── varaha_executor.py    Order placement, position management
├── varaha_monitor.py     P&L tracking, exit triggers
└── varaha_auth.py        Broker authentication (OAuth2)
```

### Execution Phases

1. **9:00 AM - Pre-market**
   - Initialize broker connection
   - Verify available margin
   - Load historical data (last 20 trading days)
   
2. **9:20 AM - Market Open**
   - Sentinel starts real-time quote loop (1-second updates)
   - Trend analyzer scores NIFTY vs SENSEX
   - Select best instrument for the day
   
3. **9:30 AM - 3:00 PM - Trading Hours**
   - Entry signal triggers (support bounce, momentum breakout)
   - Monitor position with real-time P&L
   - Partial exits at profit targets
   - Trailing stop loss on remaining position
   
4. **3:05 PM - HARD EXIT**
   - All positions force-closed (no exceptions)
   - Margin released for Kurma
   - EOD analyzer runs
   
5. **3:10 PM - Post-market**
   - Generate daily reports
   - Analyze trades, identify patterns
   - Prepare next-day setup

---

## 🧪 Broker API Testing

### Pre-Trading Checklist

Run these tests **before starting daily trading** to verify connectivity:

#### 1. Broker Configuration Test
```bash
cd /home/trading_ceo/python-trader/ShoonyaApi-py/tests
python3 -m pytest test_broker_config.py -v

# Expected: All 10 tests PASS
```

#### 2. Test Margin API
```bash
python3 << 'EOF'
from api_helper import NorenApiPy
import yaml

with open('../Shoonya_oAuthAPI-py/cred.yml') as f:
    cred = yaml.safe_load(f)

api = NorenApiPy()
if api.set_session(userid=cred['UID'], accesstoken=cred['Access_token']):
    limits = api.get_limits()
    if limits.get('stat') == 'Ok':
        print(f"✅ Margin: ₹{float(limits.get('cash')):,.2f}")
        print(f"   Collateral: ₹{float(limits.get('collateral')):,.2f}")
    else:
        print(f"❌ Error: {limits.get('emsg')}")
else:
    print("❌ Session failed")
EOF
```

#### 3. Test NIFTY OHLC Data
```bash
python3 << 'EOF'
from api_helper import NorenApiPy
import yaml
import time

with open('../Shoonya_oAuthAPI-py/cred.yml') as f:
    cred = yaml.safe_load(f)

api = NorenApiPy()
if api.set_session(userid=cred['UID'], accesstoken=cred['Access_token']):
    # NIFTY26APR25000CE token (example)
    # Find current token in varaha_master.py
    now = int(time.time())
    start = now - (3600 * 1)  # Last 1 hour
    
    ohlc = api.get_time_price_series(
        exchange='NFO',
        token='99926009',  # Update with current token
        starttime=start,
        endtime=now,
        interval=1
    )
    
    if ohlc:
        print(f"✅ NIFTY OHLC: {len(ohlc)} candles")
        print(f"   Latest: Open={ohlc[-1]['open']}, Close={ohlc[-1]['close']}")
    else:
        print("❌ No data returned")
else:
    print("❌ Session failed")
EOF
```

#### 4. Test SENSEX OHLC Data (BFO)
```bash
python3 << 'EOF'
from api_helper import NorenApiPy
import yaml
import time

with open('../Shoonya_oAuthAPI-py/cred.yml') as f:
    cred = yaml.safe_load(f)

api = NorenApiPy()
if api.set_session(userid=cred['UID'], accesstoken=cred['Access_token']):
    # SENSEX futures token (example)
    now = int(time.time())
    start = now - (3600 * 1)
    
    ohlc = api.get_time_price_series(
        exchange='BFO',
        token='825565',  # Update with current token
        starttime=start,
        endtime=now,
        interval=1
    )
    
    if ohlc:
        print(f"✅ SENSEX OHLC: {len(ohlc)} candles")
    else:
        print("❌ No data returned")
else:
    print("❌ Session failed")
EOF
```

### Full Test Suite

#### Orbiter Broker Tests (Comprehensive)
```bash
cd /home/trading_ceo/python-trader

# All broker tests
python3 -m pytest orbiter/tests/brokers/ -v

# Specific tests
python3 -m pytest orbiter/tests/brokers/test_tpSeries.py -v       # OHLC data
python3 -m pytest orbiter/tests/brokers/test_margin.py -v         # Margin API
python3 -m pytest orbiter/tests/brokers/test_connection_and_debrief.py -v  # Login/logout
```

#### Expected Output
```
test_tpSeries.py::test_bfo_tpseries_sensex_future PASSED
[BFO Future] Token: 825565 (SENSEX26MARFUT)
  Request: 2026-04-30 10:00:00 to 2026-04-30 11:00:00
  Response: 60 candles, latest close: 85248.0

test_tpSeries.py::test_nfo_tpseries_nifty PASSED
[NFO Nifty] Token: 99926009 (NIFTY26APR25000CE)
  Response: 60 candles, latest close: 245.5

test_margin.py::test_shoonya_margin_available PASSED
  Available Margin: ₹92,271.27

======================== 15 passed in 3.45s ========================
```

---

## 📍 Key Data Points

### Token Mapping (Update Daily)

NFO and BFO require numeric token IDs. These change monthly as contracts expire.

#### NIFTY Futures (NFO)
```python
# Find current NIFTY token from varaha_master.py
# Example format: NIFTY26APR25000CE (month-year-strike-type)

# To get current token:
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/trading_ceo/python-trader')
from orbiter.core.broker.master import NiftyMaster

nifty = NiftyMaster()
instruments = nifty.find_futures()
for inst in instruments[:3]:
    print(f"{inst['symbol']}: {inst['token']}")
EOF
```

#### SENSEX Futures (BFO)
```python
# Format: SENSEXMAR26FUT (month-year-FUT)

# To get current token:
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/trading_ceo/python-trader')
from orbiter.core.broker.master import SensexMaster

sensex = SensexMaster()
instruments = sensex.find_futures()
for inst in instruments[:3]:
    print(f"{inst['symbol']}: {inst['token']}")
EOF
```

### Instrument Selection Criteria

Varaha selects between NIFTY and SENSEX based on:

| Factor | Weight | How It's Scored |
|--------|--------|-----------------|
| Trend Strength | 50% | ATR, SMA, direction confirmation |
| Volatility | 30% | Historical volatility, spreads |
| Liquidity | 20% | Volume, bid-ask tightness |

**Min Score to Trade:** 5.0/10. If both < 5.0, skip the day (capital preservation first).

---

## 🔐 Authentication

### Prerequisites

1. **Broker Account** (Shoonya recommended)
   - Active trading account with ₹4,00,000+ margin

2. **Credentials File** (`Shoonya_oAuthAPI-py/cred.yml`)
   ```yaml
   Access_token: <your-oauth-token>
   Account_ID: FA333160
   Secret_Code: <from-broker-portal>
   UID: FA333160
   client_id: FA333160_U
   oauth_url: https://api.shoonya.com/NorenWeb/authorize/oauth
   ```

3. **Token Refresh** (monthly)
   ```bash
   cd /home/trading_ceo/python-trader/Shoonya_oAuthAPI-py
   python3 GetAuthcode.py
   ```

### Varaha Authentication Flow

```python
# varaha_auth.py handles this:

from api_helper import NorenApiPy
import yaml

with open('cred.yml') as f:
    cred = yaml.safe_load(f)

api = NorenApiPy()
session = api.set_session(
    userid=cred['UID'],
    accesstoken=cred['Access_token']
)

if session:
    print("✅ Authenticated, ready to trade")
    limits = api.get_limits()
    print(f"   Available margin: ₹{limits['cash']}")
else:
    print("❌ Authentication failed - refresh token")
```

---

## 📊 Position Management

### Entry Signals

#### Signal 1: Support Bounce
```
Criteria:
  - Previous candle closes > support level
  - Current candle opens below support
  - Current candle bounces back up > support with volume

Entry: On bounce above support
Position: 1 lot (size depends on volatility)
```

#### Signal 2: Momentum Breakout
```
Criteria:
  - Breakout above previous 5-candle high
  - Volume > 1.5x average
  - RSI > 60 (bullish confirmation)

Entry: On candle close above breakout
Position: 1 lot
```

### Exit Management

#### 3-Tranche System
```
Position: 1 lot

TRANCHE 1 (50%):
  Exit at: +0.5% move (e.g., NIFTY: 25,000 → 25,125)
  Locks: Initial profit

TRANCHE 2 (25%):
  Exit at: +1.0% move (e.g., NIFTY: 25,000 → 25,250)
  Locks: Additional profit

TRANCHE 3 (25%):
  Exit: Trailing SL (20-30 points behind high)
  Captures: Trend continuation
```

#### 3:05 PM Hard Exit
```
At 3:05 PM, regardless of position status:
- All open positions are FORCE CLOSED
- No market-on-close orders
- No overnight holds under any circumstances

Reason: Margin needed for Kurma at 5:20 PM
```

---

## 🛠️ Common Operations

### Daily Startup
```bash
# 1. Check credentials are fresh
cat /home/trading_ceo/python-trader/Shoonya_oAuthAPI-py/cred.yml | grep Access_token

# 2. Run pre-market tests (9:00 AM)
python3 << 'EOF'
# Run 4 tests above (margin, NIFTY, SENSEX, config)
EOF

# 3. Start Varaha (9:20 AM)
cd /home/trading_ceo/python-trader
python3 varaha_main.py

# 4. Monitor logs
tail -f /home/trading_ceo/python-trader/varaha_system.log
```

### Daily Shutdown
```bash
# Varaha auto-exits at 3:05 PM
# No manual action needed

# Check EOD report (3:15 PM)
ls -lt /home/trading_ceo/python-trader/varaha_eod_reports/ | head
cat /home/trading_ceo/python-trader/varaha_eod_reports/varaha_eod_*.txt
```

### Manual Position Check
```bash
# Get active orders
python3 << 'EOF'
from api_helper import NorenApiPy
import yaml

with open('Shoonya_oAuthAPI-py/cred.yml') as f:
    cred = yaml.safe_load(f)

api = NorenApiPy()
api.set_session(userid=cred['UID'], accesstoken=cred['Access_token'])

orders = api.get_order_list()
for order in orders:
    print(f"Order: {order['tradingsymbol']} | Qty: {order['qty']} | Status: {order['status']}")

positions = api.get_positions()
for pos in positions:
    print(f"Position: {pos['symbol']} | Qty: {pos['netqty']} | PL: ₹{pos['mtm']}")
EOF
```

### Emergency Exit (Before 3:05 PM)
```bash
# Close all positions manually
python3 << 'EOF'
from api_helper import NorenApiPy
import yaml

with open('Shoonya_oAuthAPI-py/cred.yml') as f:
    cred = yaml.safe_load(f)

api = NorenApiPy()
api.set_session(userid=cred['UID'], accesstoken=cred['Access_token'])

positions = api.get_positions()
for pos in positions:
    # Close by selling what you bought (or buying what you sold)
    sell_qty = int(pos['netqty'])
    if sell_qty > 0:  # Long position - sell to close
        api.place_order(
            buy_or_sell='S',
            product_type='I',
            exchange='NFO',
            tradingsymbol=pos['symbol'],
            quantity=abs(sell_qty),
            discloseqty=0,
            price_type='MKT',
            price=0
        )
    elif sell_qty < 0:  # Short position - buy to close
        api.place_order(
            buy_or_sell='B',
            product_type='I',
            exchange='NFO',
            tradingsymbol=pos['symbol'],
            quantity=abs(sell_qty),
            discloseqty=0,
            price_type='MKT',
            price=0
        )

print("✅ All positions closed")
EOF
```

---

## 📈 Performance Metrics

### Daily P&L Tracking
```bash
# View yesterday's report
cat /home/trading_ceo/python-trader/varaha_eod_reports/varaha_eod_2026-04-29.txt

# Expected format:
# Date: 2026-04-29
# Instrument Selected: NIFTY
# Trades Executed: 2
# Winning Trades: 1 (+₹2,500)
# Losing Trades: 1 (-₹800)
# Net P&L: +₹1,700
# Sharpe Ratio: 1.45
# Win Rate: 50%
# Recommendation: Stay with NIFTY, increase position on strong trends
```

### Monthly Summary
```bash
# Aggregate all EOD reports
for f in /home/trading_ceo/python-trader/varaha_eod_reports/varaha_eod_*.txt; do
    grep "Net P&L\|Instrument Selected" "$f"
done | paste - - | awk '{sum+=$4; print $0} END {print "Total P&L: " sum}'
```

---

## 🐛 Troubleshooting

### "Session Expired: Invalid Session Key"
```bash
# Token expired (>30 days old)
cd /home/trading_ceo/python-trader/Shoonya_oAuthAPI-py
python3 GetAuthcode.py
```

### "Insufficient margin"
```bash
# Check available funds
python3 << 'EOF'
from api_helper import NorenApiPy
import yaml

with open('cred.yml') as f:
    cred = yaml.safe_load(f)

api = NorenApiPy()
api.set_session(userid=cred['UID'], accesstoken=cred['Access_token'])
limits = api.get_limits()

cash = float(limits.get('cash', 0))
used = float(limits.get('payin', 0)) - cash
print(f"Available: ₹{cash:,.0f}")
print(f"Used: ₹{used:,.0f}")
print(f"Total: ₹{float(limits.get('payin', 0)):,.0f}")

if cash < 100000:
    print("\n⚠️ LOW MARGIN - Cannot start new positions")
EOF
```

### "MCX segment not enabled"
This only applies to Flattrade. For Varaha using NFO/BFO on Shoonya, this shouldn't occur.
```bash
# Verify broker is Shoonya
cat /home/trading_ceo/python-trader/Shoonya_oAuthAPI-py/cred.yml | head -1
```

### "NIFTY/SENSEX token not found"
Token IDs change monthly. Update varaha_master.py:
```bash
# 1. Get latest tokens
python3 varaha_master.py --refresh-tokens

# 2. Verify tokens in log
grep "NIFTY\|SENSEX" /home/trading_ceo/python-trader/varaha_system.log | tail -5
```

---

## 📚 Documentation Reference

| Document | Purpose |
|----------|---------|
| `BROKER_API_TESTING_GUIDE.md` | All test files, how to run, expected output |
| `TOKEN_GENERATION_GUIDE.md` | OAuth token automation (GetAuthcode.py) |
| `CREDENTIALS_README.md` | Credential file fields and lifecycle |
| `BROKER_AUTHENTICATION_GUIDE.md` | Broker setup, troubleshooting |
| `varaha_system.log` | Real-time operation logs |
| `varaha_eod_reports/` | Daily trade analysis and insights |

---

## ⚠️ Critical Rules

1. **HARD EXIT at 3:05 PM** — All positions closed, no exceptions
2. **No overnight holds** — All must be closed by 3:30 PM
3. **Margin verification** — Check ≥ ₹4,00,000 before starting
4. **Token freshness** — Refresh every 30 days or when "Invalid Session" appears
5. **Pre-trading checklist** — Run 4 tests above before 9:20 AM opens
6. **Capital preservation** — Skip days with scores < 5.0
7. **Monitor spreads** — If bid-ask > 10 points, reduce position size

---

## 🔄 Integration with Kurma

```
9:00 AM   ┌─────────────────────────┐
          │ Varaha Pre-market        │
          │ (authenticate, verify)   │
          └─────────────────────────┘
             ↓
9:20 AM   ┌─────────────────────────┐
          │ Varaha Trading Starts    │
          │ (enter/manage positions) │
          └─────────────────────────┘
             ↓
3:05 PM   ┌─────────────────────────┐
          │ Varaha FORCE EXIT        │ ← Margin released
          │ (close all positions)    │
          └─────────────────────────┘
             ↓
5:10 PM   ┌─────────────────────────┐
          │ Kurma Selector Starts    │ ← Receives ₹4,00,000
          │ (scores commodities)     │
          └─────────────────────────┘
             ↓
5:20 PM   ┌─────────────────────────┐
          │ Kurma Trading Starts     │
          │ (same margin, commodities)│
          └─────────────────────────┘
             ↓
11:15 PM  ┌─────────────────────────┐
          │ Kurma FORCE EXIT         │ ← Margin released
          │ (close all positions)    │
          └─────────────────────────┘

NEXT DAY 9:20 AM: Full cycle repeats
```

---

**Last Updated:** 2026-04-30  
**Status:** ✅ Ready for Production  
**Broker:** Shoonya (OAuth2)  
**Testing:** Complete with 15+ test files
