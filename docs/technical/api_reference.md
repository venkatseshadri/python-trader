# 📖 API Reference

## Core Engine

### `OrbiterState`
**Location:** `core/engine/state.py`

The central context object.

| Attribute | Type | Description |
| :--- | :--- | :--- |
| `client` | `BrokerClient` | Reference to the broker interface. |
| `active_positions` | `dict` | Key: Token, Value: Dict of entry details (price, time, strategy). |
| `last_scan_metrics` | `list` | Buffer of the latest evaluation scores for logging. |
| `config` | `dict` | Merged runtime configuration. |

### `Evaluator`
**Location:** `core/engine/evaluator.py`

Calculates technical scores.

#### `evaluate_filters(state, token)`
- **Input:** `OrbiterState`, `token` (str)
- **Output:** `float` (Total Score)
- **Logic:**
    1.  Fetches 1-minute candles from `BrokerClient`.
    2.  Resolves OHLC stats.
    3.  Iterates through active `filters`.
    4.  Weighted sum of filter scores.

### `Executor`
**Location:** `core/engine/executor.py`

Execution and Risk Management.

#### `rank_signals(state, scores, syncer)`
- **Input:** `scores` (dict of token: score)
- **Logic:** Sorts tokens by score magnitude. Picks top N. Checks if already in position. Places orders.

#### `check_sl(state, syncer)`
- **Logic:** Loops through `active_positions`. Calculates current P&L. Evaluates Exit Filters (`sl/*.py`, `tp/*.py`). Triggers square-off if hit.

---

## Broker Layer

### `BrokerClient`
**Location:** `core/broker/__init__.py`

The unified wrapper.

#### `get_ltp(key)`
Returns the Last Traded Price from the local WebSocket cache (`SYMBOLDICT`).

#### `place_future_order(**kwargs)`
Resolves the correct "Near Month" contract and places a market order.

#### `place_put_credit_spread(**kwargs)`
Complex logic to find:
1.  ATM Strike.
2.  Hedge Strike (OTM).
3.  Places a 2-leg order (Buy Hedge, Sell ATM).

### `ConnectionManager`
**Location:** `core/broker/connection.py`

#### `login(factor2_override=None)`
Authenticates with Shoonya. supports interactive 2FA input if `factor2_override` is missing.

#### `start_live_feed(symbols, callback)`
Starts a background thread for WebSocket ticks.
