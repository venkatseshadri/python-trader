# Varaha Safety Gate - Documentation

## 🛡️ Purpose

The Safety Gate system prevents duplicate orders even if the script crashes and restarts. It acts as a "Source of Truth" by querying the broker's live orderbook before placing any trade.

## 📋 Components

### Step 1: Orderbook Validator (`varaha_executor.py`)

Added `is_already_traded(token, side)` method that:
- Queries Shoonya `get_order_book()` API
- Filters for token + side (BUY/SELL) combination
- Returns `True` if order exists with status COMPLETE/OPEN/PENDING

```python
def is_already_traded(self, token: str, side: str) -> bool:
    """Check if token + side already in orderbook"""
    book = self.api.get_order_book()
    # ... checks for existing order
    return True/False
```

### Step 2: Pre-Placement Check (`varaha_executor.py`)

Updated `place_varaha_order()` to:
- Call `is_already_traded()` before placing order
- Log "DUPLICATE BLOCKED" if order exists
- Skip placement if duplicate detected

### Step 3: Session Recovery (`varaha_main.py`)

Added two functions:
- `check_existing_positions(engine, dry_run)` - Queries position book for active Iron Butterfly
- `start_monitoring_from_recovery(engine, positions, dry_run)` - Resumes monitoring

On startup, the orchestrator now:
1. Authenticates (Phase 1)
2. **Checks for existing positions** ← NEW
3. If found → Resume monitoring (skip execution)
4. If not found → Continue to execution

## 🔄 Flow

```
Script Start
    ↓
Authenticate
    ↓
check_existing_positions()
    ↓
┌─────────────┐
│ Positions? │
└─────────────┘
    ↓        ↓
   YES      NO
    ↓        ↓
Resume     Execute New
Monitor   Iron Butterfly
    ↓
TSL Start
```

## 📝 Changes Summary

| File | Change |
|------|-------|
| `varaha_executor.py` | Added `is_already_traded()` method |
| `varaha_executor.py` | Updated `place_varaha_order()` with duplicate check |
| `varaha_main.py` | Added `check_existing_positions()` function |
| `varaha_main.py` | Added `start_monitoring_from_recovery()` function |
| `varaha_main.py` | Updated `run_orchestrator()` with session recovery |

## ✅ Test Cases

### Atomic Order Test (Step 4)
- Mock: Fake orderbook with NIFTY 24000 CE Buy order
- Action: Command bot to enter Iron Butterfly for same strike
- Expectation: Bot logs "Duplicate blocked" and skips API call

---

*Updated: Apr 20, 2026*