# MCX Session Post-Mortem Report
## Date: March 4, 2026 | Session: MCX (5:00 PM - 11:15 PM IST)

---

## 1. Session Overview

| Metric | Value |
|--------|-------|
| Mode | Paper Trading (SIMULATION) |
| Instruments | 10 (CRUDEOIL, NATURALGAS, GOLD, SILVER, COPPER, ZINC, LEAD, ALUMINIUM, NICKEL, GOLDPETAL) |
| Threshold | 0.4 pts |
| Real Trades | 0 |
| Simulated Orders | 10,316 |

---

## 2. Scores Analysis

### Instruments Reaching Threshold (0.4+)

| Instrument | Max Score | Time Above 0.4 | Status |
|------------|-----------|-----------------|--------|
| **CRUDEOIL** | 0.42 | ~45 mins (17:28-18:00 IST) | Should have traded |
| **NATURALGAS** | 0.41 | ~30 mins (17:42-18:00 IST) | Should have traded |

### Other Instruments

| Instrument | Max Score | Notes |
|------------|-----------|-------|
| COPPER | 0.30 | Close but below threshold |
| LEAD | 0.30 | Close but below threshold |
| NICKEL | 0.30 | Close but below threshold |
| ZINC | 0.32 | Close but below threshold |
| ALUMINIUM | 0.29 | Below threshold |
| SILVER | 0.07 | Very low |
| GOLD | 0.00 | No data/bars |
| GOLDPETAL | 0.00 | No data/bars |

---

## 3. Root Cause Analysis

### Issue #1: ADX Always Zero 🔴

**Observation:**
- `market_adx: 0.0` in ALL score calculations
- This severely impacts the scoring formula:
  ```
  score = market_adx * weight_adx + (ema_slope) * weight_ema + supertrend_direction * weight_supertrend
  ```

**Impact:**
- With ADX = 0, the ADX component contributes 0 to the score
- Only EMA slope and SuperTrend direction contribute
- Even when EMA and SuperTrend align, max possible score is limited

**Fix Required:**
- Debug why ADX indicator returns 0
- Check if correct timeframe/data is being used
- Verify ADX calculation parameters (period=14)

---

### Issue #2: Order Logic Bug 🔴

**Observation:**
- 10,316 simulated orders placed
- Both BUY and SELL orders placed simultaneously for same instrument
- Example: `side=BUY` and `side=SELL` for CRUDEOILM19MAR26 at same timestamp

**Impact:**
- Orders cancel each other out
- No net position taken
- Confuses the system

**Fix Required:**
- Check filter logic for direction (LONG vs SHORT)
- Prevent simultaneous opposite orders
- Add order cooldown period

---

### Issue #3: Some Instruments Have No Data 🟡

| Instrument | Issue |
|------------|-------|
| GOLD | Token maps correctly but Bars = 0 |
| GOLDPETAL | Recently added, needs verification |

---

## 4. Threshold Analysis

**Current: 0.4**

| Assessment | Evidence |
|------------|----------|
| **Too High?** | CRUDEOIL hit 0.42 for 45+ mins but NO trade executed |
| **Root Cause** | Order logic bug prevented execution |
| **Recommendation** | Keep at 0.4 once bugs fixed, then evaluate |

---

## 5. Margin Analysis

### Required Margin per Instrument (from span_cache)

| Instrument | Total Margin (₹) | Notes |
|------------|------------------|-------|
| CRUDEOIL | 47,717 | MINI - OK for 1 lot |
| NATURALGAS | 2,41,209 | HIGH - expensive! |
| GOLD | N/A | Data not loading |
| SILVER | 68,56,252 | VERY HIGH - avoid |
| COPPER | 8,20,591 | HIGH |
| ZINC | 3,41,400 (LEAD) | Already using MINI |
| LEAD | 3,41,400 | MINI |
| ALUMINIUM | 3,41,400 | MINI |
| NICKEL | 1,16,044 | Reasonable |

**Recommendation:**
- Focus on: CRUDEOIL, LEAD, ALUMINIUM, NICKEL (lower margin)
- Avoid: SILVER (too expensive), NATURALGAS (high margin)

---

## 6. Filter Performance

### Current Filters (from filters.json)
- ADX (threshold: 20) - **NOT WORKING** (always returns 0)
- EMA Fast (period: 5) - Working
- EMA Slow (period: 9) - Working
- SuperTrend (period: 10, multiplier: 3) - Working

### Weights
- weight_adx: 0.4
- weight_ema_slope: 0.3
- weight_supertrend: 0.3

**Issue:** With ADX broken, only 60% of weight system is working

---

## 7. Action Items

### Critical (Fix Before Next Session)
1. **Fix ADX calculation** - Check data feed and indicator parameters
2. **Fix order logic** - Prevent duplicate BOTH BUY and SELL orders
3. **Verify trade execution** - Ensure orders actually fire when threshold crossed

### Important
4. **Add GOLDPETAL to mcx_futures_map.json** - Persist token mapping
5. **Check GOLD token** - Still showing no bars

### Enhancement Ideas
6. Consider adding RSI, MACD as backup indicators
7. Add News sentiment (optional)
8. Lower threshold to 0.35 temporarily while ADX is broken

---

## 8. Tomorrow's Plan

1. Fix ADX indicator
2. Fix order duplication bug
3. Run paper trading again
4. Monitor if trades execute properly
5. Review at end of session

---

## Appendix: Debug Logs

### Sample Score Calculation (CRUDEOIL at 17:59 IST)
```
market_adx: 0.0
market_ema_fast: 6885.59
market_ema_slow: 6870.49
market_supertrend_dir: 1
filter_supertrend_direction_numeric: -1
Score: 0.42 (despite ADX=0!)
```

### Issue: SuperTrend Direction Mismatch
- `market_supertrend_dir: 1` (market says UP)
- `filter_supertrend_direction_numeric: -1` (filter says DOWN)
- These are OPPOSITE - causes score reduction

---

*Report generated: 2026-03-04 18:35 IST*
