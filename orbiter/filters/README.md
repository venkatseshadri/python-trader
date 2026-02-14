# Technical Strategy Filters

This directory houses the technical analysis modules used to score potential entries and monitor active exits.

## Structure

### 1. `common/` (Agnostic Technicals)
Mathematical filters that work identically across all markets.
*   **`orb.py`**: Opening Range Breakout (Parameterized for any session start time).
*   **`ema5.py`**: LTP vs 5-period Exponential Moving Average.
*   **`ema_cross.py`**: 5-period EMA vs 9-period EMA crossover.
*   **`supertrend.py`**: Trend bias scoring based on Supertrend line distance.

### 2. `sl/` & `tp/` (Risk Management)
Logic for determining when to exit a position.
*   **Direction-Aware**: These filters automatically detect if you are in a Spread or a Future (Long/Short) and adjust their terminology and logic accordingly.
*   **PnL Normalization**: All risk filters operate on a "Positive = Profit" basis.

## The Filter Factory
`orbiter/filters/__init__.py` acts as a centralized factory. The engine calls `get_filters(filter_type, segment_name)` to retrieve the implementation classes relevant to the current trading session.

---

## 🛠 Developer Guide: Adding New Filters

To add a new technical filter to the Orbiter engine:

### 1. Create the Filter File
Add a new `.py` file in `filters/common/` (for technicals) or `filters/sl/` or `filters/tp/` (for risk management).

### 2. Implement the Logic
Each filter must expose a `key` and an `evaluate` function.

**Example Entry Filter:**
```python
# filters/common/my_new_filter.py

def my_new_filter(data, candles, **kwargs):
    # 'data' contains current tick (LTP, high, low)
    # 'candles' contains historical 1m data
    ltp = data.get('lp', 0)
    score = 1.0 if ltp > some_threshold else 0.0
    return {'score': score, 'extra_info': 'Optional metadata'}
```

### 3. Register in the Factory
Import and add your filter to the `FILTERS` list in `orbiter/filters/__init__.py`.

```python
from .common.my_new_filter import my_new_filter
# ...
Filter('ef5_my_new_filter', 'entry', my_new_filter),
```

### 4. Adjust Weights
If it's an entry filter, update `ENTRY_WEIGHTS` in `config/main_config.py` to include a weight for your new filter.
