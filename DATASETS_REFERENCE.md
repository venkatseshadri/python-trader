# Trading Datasets Reference Guide

Complete documentation of all historical and test datasets available for backtesting and analysis.

---

## 📊 Dataset Summary

| Dataset | Type | Size | Location | Records | Purpose |
|---------|------|------|----------|---------|---------|
| **NIFTY 50 Equity Data** | CSV | 4.8 GB | `nifty_data/` | 1M+ per stock | Backtesting equity strategies |
| **MCX Test Data** | JSON | 480 KB | `orbiter/test_data/` | Multiple instruments | MCX futures validation |
| **NFO Test Data** | JSON | 73 KB | `orbiter/test_data/` | NIFTY index | NIFTY futures validation |
| **BFO Test Data** | JSON | 16 KB | `orbiter/test_data/` | SENSEX index | SENSEX futures validation |
| **Kurma EOD Reports** | JSON/TXT | 184 KB | `kurma_eod_reports/` | ~20 sessions | Live trading records (Apr 30) |
| **Cache Data** | JSON | 196 KB | `orbiter/data/` | Span, ADX, masters | Runtime calculation cache |

---

## 1️⃣ NIFTY 50 Equity Minute-Level Data

### Location
```
/home/trading_ceo/python-trader/nifty_data/
```

### Dataset Characteristics
- **Total Files:** 105 CSV files (4.8 GB)
- **Data Type:** Minute-level OHLCV (Open, High, Low, Close, Volume)
- **Time Period:** Feb 2, 2015 → Jan 22, 2026 (~11 years)
- **Update Frequency:** Last updated: Mar 3, 2026

### File Structure

**Format:** CSV with 5 columns
```
date,open,high,low,close,volume
2015-02-02 09:15:00,216.45,217.15,216.3,216.4,229342
2015-02-02 09:16:00,216.4,216.55,216.0,216.0,97732
```

### Instruments Covered (105 Total)

**Nifty 50 Index Components:**
1. ABB (51M)
2. ADANIENSOL (47M)
3. ADANIENT (49M)
4. ADANIGREEN (35M)
5. ADANIPORTS (50M)
6. ADANIPOWER (46M)
7. AMBUJACEM (50M)
8. APOLLOHOSP (52M)
9. ASIANPAINT (52M)
10. ATGL (48M)
... and 95 more

**Index Data:**
- NIFTY 50_minute.csv (comprehensive index data)
- NIFTY BANK_minute.csv (Nifty Bank sub-index)

### Data Quality

**Example: RELIANCE_minute.csv**
- **Total Records:** 1,014,859 (11 years of minute data)
- **Date Range:** 2015-02-02 09:15:00 → 2026-01-22 14:41:00
- **Records per Day:** ~250-280 (NSE trading hours: 9:15 AM - 3:30 PM)

### Use Cases for Backtesting

✅ **Equity Intraday Strategies**
```python
# Load RELIANCE minute data for backtesting
df = pd.read_csv('nifty_data/RELIANCE_minute.csv')
df['date'] = pd.to_datetime(df['date'])

# Filter to trading hours (9:15 AM - 3:30 PM)
# Apply momentum, RSI, moving average filters
# Backtest entry/exit logic
```

✅ **Momentum Analysis**
- Identify trending stocks during peak hours (10:00-11:30 AM, 2:00-3:30 PM)
- Volume spikes and breakouts

✅ **Portfolio Construction**
- Select top movers from 50 stocks
- Correlation analysis

✅ **Parameter Optimization**
- Test different MA periods (5, 10, 20 min)
- Volatility thresholds
- Risk/reward ratios

### Data Validation

**Gaps to Check:**
- Market holidays (NSE closed: weekends, national holidays)
- Corporate actions (splits, dividends — not adjusted)
- Extreme spikes (data quality issues)

**Known Characteristics:**
- No dividends/splits adjustment
- Intraday bars only (no daily aggregate)
- No overnight gaps (market close → next day open)

---

## 2️⃣ MCX Commodity Futures Test Data

### Location
```
/home/trading_ceo/python-trader/orbiter/test_data/mcx_instrument_data.json
```

### Dataset Characteristics
- **Size:** 480 KB
- **Format:** JSON (nested by instrument)
- **Date:** March 16, 2026 (single day, multiple time periods)
- **Purpose:** Validation/testing for MCX OHLC data fetch

### Data Structure

```json
{
  "GOLD": {
    "token": "477176",
    "candles": [
      {
        "stat": "Ok",
        "time": "16-03-2026 18:20:00",
        "ssboe": "1773665400",        // Epoch timestamp
        "into": "156993.00",          // Intraday Open
        "inth": "156993.00",          // Intraday High
        "intl": "156809.00",          // Intraday Low
        "intc": "156809.00",          // Intraday Close
        "intvwap": "156881.77",       // VWAP
        "intv": "53",                 // Intraday Volume
        "intoi": "3",                 // Open Interest change
        "v": "19444",                 // Cumulative Volume
        "oi": "29730"                 // Cumulative Open Interest
      }
    ]
  }
}
```

### Instruments in MCX Test Data

- **GOLD** — Gold futures (token: 477176)
- **CRUDEOIL** — Crude oil futures (token: varies)
- **NATURALGAS** — Natural gas futures
- Other commodities as applicable

### Field Definitions

| Field | Meaning | Type | Example |
|-------|---------|------|---------|
| `token` | Shoonya token ID | String | "477176" |
| `into` | Intraday open price | Float | 156993.00 |
| `inth` | Intraday high price | Float | 156993.00 |
| `intl` | Intraday low price | Float | 156809.00 |
| `intc` | Intraday close price | Float | 156809.00 |
| `intvwap` | Volume-weighted avg price | Float | 156881.77 |
| `intv` | Volume traded | Integer | 53 |
| `intoi` | Change in open interest | Integer | 3 |
| `v` | Cumulative volume | Integer | 19444 |
| `oi` | Cumulative open interest | Integer | 29730 |
| `ssboe` | Seconds since beginning of epoch | Timestamp | 1773665400 |

### Use Cases for Backtesting

✅ **Kurma MCX Strategy Testing**
```python
# Load MCX test data
import json
with open('orbiter/test_data/mcx_instrument_data.json') as f:
    mcx_data = json.load(f)

# Get GOLD candles
gold_candles = mcx_data['GOLD']['candles']

# Test entry signals: support bounce, momentum
for candle in gold_candles:
    price = float(candle['intc'])
    volume = int(candle['intv'])
    # Apply Kurma selector logic
```

⚠️ **Limitations:**
- Single day only (March 16, 2026)
- Limited to specific instruments
- For validation, not comprehensive backtesting

---

## 3️⃣ NFO (NIFTY Futures/Options) Test Data

### Location
```
/home/trading_ceo/python-trader/orbiter/test_data/nfo_index_data.json
```

### Dataset Characteristics
- **Size:** 73 KB
- **Format:** JSON (similar structure to MCX)
- **Date:** March 16, 2026
- **Purpose:** NIFTY futures/options validation

### Data Structure
Same as MCX data (see Section 2):
- OHLC prices (intraday)
- Volume and open interest
- VWAP calculations

### Instruments in NFO Test Data

- **NIFTY Futures** — NIFTY50 index futures
- **NIFTY Options** — Call/Put options (various strikes)
- **NIFTY Bank** — NIFTY Bank index futures

### Example Candle
```json
{
  "stat": "Ok",
  "time": "16-03-2026 15:05:00",
  "ssboe": "1773653700",
  "into": "23403.55",
  "inth": "23458.00",
  "intl": "23403.55",
  "intc": "23440.20",
  "v": "0",
  "oi": "0"
}
```

### Use Cases for Backtesting

✅ **Varaha NFO Strategy Testing**
- NIFTY trend following signals
- Support/resistance identification
- Entry quality scoring

⚠️ **Limitations:**
- Single day (March 16, 2026)
- No multi-day trend data
- For validation only

---

## 4️⃣ BFO (SENSEX Futures/Options) Test Data

### Location
```
/home/trading_ceo/python-trader/orbiter/test_data/bfo_index_data.json
```

### Dataset Characteristics
- **Size:** 16 KB
- **Format:** JSON
- **Date:** March 16, 2026
- **Purpose:** SENSEX futures validation

### Instruments
- SENSEX Futures
- SENSEX Options

### Use Cases
- Varaha alternative instrument validation
- Comparison with NIFTY data

---

## 5️⃣ Kurma EOD Reports (Live Trading Records)

### Location
```
/home/trading_ceo/python-trader/kurma_eod_reports/
```

### Dataset Characteristics
- **Format:** JSON + TXT pairs
- **Date Range:** April 30, 2026
- **Sessions:** ~20 trading sessions
- **Size:** 184 KB total

### File Naming Convention
```
kurma_eod_YYYYMMDD_HHMMSS.json   # Machine-readable report
kurma_eod_YYYYMMDD_HHMMSS.txt    # Human-readable summary
```

### JSON Structure

```json
{
  "timestamp": "2026-04-30T19:05:42.259549",
  "trade_analysis": {
    "total_trades": 2,
    "total_pnl": 11500,
    "winners": 2,
    "losers": 0,
    "win_rate": 100.0,
    "trades": [
      {
        "trade_id": "KURMA_20260430_001",
        "instrument": "NATGASM",
        "entry_price": 9110,
        "entry_signal": "support_bounce",
        "entry_quality": 8.0,
        "total_pnl": 5750,
        "win_loss": "WIN",
        "tranche_1_pnl": 1250,
        "tranche_2_pnl": 2500,
        "tranche_3_pnl": 2000,
        "holding_time_minutes": 45,
        "exit_quality": 7.5,
        "r_ratio": 1.8
      }
    ],
    "market_analysis": {
      "best_instrument": "NATGASM",
      "best_score": 7.8,
      "trend": "bullish",
      "volatility": "medium"
    }
  }
}
```

### Key Fields

| Field | Meaning | Example |
|-------|---------|---------|
| `trade_id` | Unique trade identifier | KURMA_20260430_001 |
| `instrument` | Commodity traded | NATGASM |
| `entry_signal` | Entry reason | support_bounce |
| `entry_quality` | Signal quality (0-10) | 8.0 |
| `total_pnl` | Profit/loss in rupees | 5750 |
| `win_loss` | Trade outcome | WIN |
| `tranche_X_pnl` | Exit profit per tranche | 1250 |
| `holding_time_minutes` | Minutes held | 45 |
| `r_ratio` | Risk/Reward ratio | 1.8 |

### Text Summary Example
```
═══════════════════════════════════════════════════════════
KURMA EOD REPORT - 2026-04-30 19:05:42
═══════════════════════════════════════════════════════════

TRADE STATISTICS
├─ Total Trades: 2
├─ Winners: 2 (100.0%)
├─ Losers: 0
├─ Avg P&L: ₹5,750
└─ Total P&L: ₹11,500

BEST TRADE
├─ Instrument: NATGASM
├─ Entry: support_bounce @ ₹9,110
├─ Exit: 3-tranche (50/25/25)
└─ P&L: ₹5,750 (WIN)

MARKET ANALYSIS
├─ Best Instrument: NATGASM (score: 7.8)
├─ Trend: bullish
└─ Volatility: medium
```

### Use Cases for Backtesting

✅ **Live Trading Validation**
- Compare backtest results with actual trades
- Identify gaps between simulation and reality
- Slippage analysis

✅ **Parameter Tuning**
- Which entry signals work best
- Optimal TP levels
- Position sizing improvements

✅ **Walk-Forward Testing**
- Recent trading data (April 30, 2026)
- Real market conditions
- Current parameter effectiveness

---

## 6️⃣ Cache & Reference Data

### Location
```
/home/trading_ceo/python-trader/orbiter/data/
```

### Files

#### span_cache.json (14 KB)
- SPAN margin calculations for futures
- Updated: Apr 5
- Purpose: Margin requirement validation
- **Don't use for backtesting** (runtime optimization)

#### adx_cache.json (115 bytes)
- ADX indicator values
- Last updated: Apr 1
- Purpose: Technical indicator caching
- **Don't use for backtesting** (calculate fresh)

#### futures_master.json (127 KB)
- Master list of all futures contracts
- Token mappings (symbol → token ID)
- Lot sizes, multipliers, expiry dates
- **Use for:** Token lookup during backtesting

**Example:**
```json
{
  "CRUDEOILM": {
    "token": "488291",
    "expiry": "2026-05-18",
    "lot_size": 10,
    "tick_size": 1,
    "multiplier": 10
  }
}
```

#### mcx_futures_map.json & nfo_futures_map.json
- Quick lookup: symbol → token
- Minimal file size
- Use for real-time token resolution

#### mcx/ & nfo/ directories
- Instrument metadata
- Strike prices (for options)
- Contract specifications

---

## 📈 How to Use These Datasets for Backtesting

### 1. Equity Strategy Backtesting (Using NIFTY Data)

```python
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('nifty_data/RELIANCE_minute.csv')
df['date'] = pd.to_datetime(df['date'])

# Filter trading hours (9:15 AM - 3:30 PM)
df['hour'] = df['date'].dt.hour
df['minute'] = df['date'].dt.minute
trading_hours = ((df['hour'] == 9) & (df['minute'] >= 15)) | \
                ((df['hour'] > 9) & (df['hour'] < 15)) | \
                ((df['hour'] == 15) & (df['minute'] <= 30))
df_filtered = df[trading_hours].copy()

# Calculate indicators
df_filtered['MA5'] = df_filtered['close'].rolling(5).mean()
df_filtered['MA20'] = df_filtered['close'].rolling(20).mean()

# Simple strategy: MA crossover
df_filtered['signal'] = 0
df_filtered.loc[df_filtered['MA5'] > df_filtered['MA20'], 'signal'] = 1
df_filtered.loc[df_filtered['MA5'] < df_filtered['MA20'], 'signal'] = -1

# Calculate returns
df_filtered['returns'] = df_filtered['close'].pct_change()
df_filtered['strategy_returns'] = df_filtered['signal'].shift(1) * df_filtered['returns']

# Backtest metrics
total_return = (1 + df_filtered['strategy_returns']).prod() - 1
sharpe = df_filtered['strategy_returns'].mean() / df_filtered['strategy_returns'].std() * np.sqrt(252*6.5*60)

print(f"Total Return: {total_return:.2%}")
print(f"Sharpe Ratio: {sharpe:.2f}")
```

### 2. MCX/NFO Futures Backtesting (Using Test Data)

```python
import json
from datetime import datetime

# Load MCX test data
with open('orbiter/test_data/mcx_instrument_data.json') as f:
    mcx_data = json.load(f)

# Extract GOLD candles
gold = mcx_data['GOLD']
candles = gold['candles']

# Build dataframe
df = pd.DataFrame(candles)
df['time'] = pd.to_datetime(df['time'], format='%d-%m-%Y %H:%M:%S')
df['close'] = df['intc'].astype(float)
df['volume'] = df['intv'].astype(int)

# Apply Kurma selector logic
# Score based on: trend, volatility, liquidity
# Calculate momentum, ATR, RSI

# Test entry/exit signals
# Evaluate TP levels and TSL effectiveness
```

### 3. Live Trading Record Analysis

```python
import json
import glob

# Load all EOD reports
reports = []
for file in glob.glob('kurma_eod_reports/*.json'):
    with open(file) as f:
        reports.append(json.load(f))

# Analyze patterns
df_trades = pd.DataFrame()
for report in reports:
    for trade in report['trade_analysis']['trades']:
        df_trades = pd.concat([df_trades, pd.DataFrame([trade])], ignore_index=True)

# Statistics
print(f"Win Rate: {(df_trades['win_loss'] == 'WIN').sum() / len(df_trades):.1%}")
print(f"Avg P&L: ₹{df_trades['total_pnl'].mean():,.0f}")
print(f"Best Trade: ₹{df_trades['total_pnl'].max():,.0f}")
print(f"Worst Trade: ₹{df_trades['total_pnl'].min():,.0f}")

# By instrument
print("\nP&L by Instrument:")
print(df_trades.groupby('instrument')['total_pnl'].agg(['sum', 'mean', 'count']))

# By entry signal
print("\nP&L by Entry Signal:")
print(df_trades.groupby('entry_signal')['total_pnl'].agg(['sum', 'mean', 'count']))
```

---

## ⚠️ Important Considerations

### Data Quality Issues

1. **NIFTY CSV Data**
   - No dividend/split adjustment
   - Gaps on holidays (NSE closed)
   - May have data quality issues in early years (2015-2016)
   - Test by checking volume anomalies

2. **Test Data (JSON)**
   - Single day only (March 16, 2026)
   - Limited instruments
   - Use for validation, not production backtesting

3. **EOD Reports**
   - April 30, 2026 only
   - ~20 sessions
   - Real but limited sample size
   - Seasonal/market regime specific

### Backtesting Best Practices

✅ **DO:**
- Adjust for corporate actions if available
- Account for trading hours (9:15 AM - 3:30 PM NSE)
- Include slippage (bid-ask spread, volume impact)
- Walk-forward testing on out-of-sample data
- Compare with live trading results (Apr 30 data)

❌ **DON'T:**
- Use full 11 years naively (market regime changed)
- Ignore fat-tail risks (black swan events)
- Overfit to test data
- Forget transaction costs
- Test on data you plan to trade live

---

## 🎯 Recommended Workflow

### Phase 1: Development (Test Data)
```
Use: BFO, MCX, NFO test data (JSON)
Goal: Validate logic with small dataset
Time: 1-2 days
```

### Phase 2: Backtesting (NIFTY CSV Data)
```
Use: 2-3 years of NIFTY data (most recent)
Goal: Comprehensive backtest of strategy
Time: 1-2 weeks
```

### Phase 3: Walk-Forward Testing
```
Use: Rolling windows of NIFTY data
Goal: Avoid overfitting, validate robustness
Time: 1-2 weeks
```

### Phase 4: Live Validation
```
Use: Apr 30 EOD reports + new live trades
Goal: Compare backtest vs actual performance
Time: Ongoing
```

---

## 📚 File Index for Quick Lookup

| Use Case | Dataset | Location | Size | Period |
|----------|---------|----------|------|--------|
| Quick validation | MCX/NFO JSON | `orbiter/test_data/` | 569 KB | 1 day |
| Equity backtest | NIFTY CSV | `nifty_data/` | 4.8 GB | 11 yrs |
| Futures backtest | Test JSON | `orbiter/test_data/` | 569 KB | 1 day |
| Live analysis | EOD reports | `kurma_eod_reports/` | 184 KB | 1 day |
| Token lookup | Masters | `orbiter/data/` | 127 KB | Current |

---

## 🔧 Setup for Backtesting

### Create Backtest Environment
```bash
# Copy datasets to isolated folder
mkdir -p /home/trading_ceo/backtest_data
cp -r nifty_data /home/trading_ceo/backtest_data/
cp orbiter/test_data/*.json /home/trading_ceo/backtest_data/

# Create backtest script
cat > /home/trading_ceo/backtest_runner.py << 'EOF'
import pandas as pd
import json
from pathlib import Path

DATA_PATH = Path('/home/trading_ceo/backtest_data')

def load_nifty_data(symbol='RELIANCE'):
    df = pd.read_csv(DATA_PATH / f'nifty_data/{symbol}_minute.csv')
    df['date'] = pd.to_datetime(df['date'])
    return df

def load_mcx_data():
    with open(DATA_PATH / 'mcx_instrument_data.json') as f:
        return json.load(f)

def load_nfo_data():
    with open(DATA_PATH / 'nfo_index_data.json') as f:
        return json.load(f)

# Your backtest code here
EOF
```

---

**Last Updated:** April 30, 2026  
**Data Quality:** Verified for Kurma testing  
**Next Review:** May 31, 2026  
**Backtest Status:** Ready for comprehensive strategy validation
