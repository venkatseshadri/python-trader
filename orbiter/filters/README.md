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
