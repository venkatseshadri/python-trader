# 🏗️ Orbiter Architecture & Key Decisions

## Core Components

1.  **`main.py` (Controller):**
    - Determines Active Segment (NFO vs MCX) based on time.
    - Initializes `BrokerClient` (specific to the segment).
    - Runs the infinite loop (Evaluation -> Execution -> Sync).

2.  **`core/broker/__init__.py` (BrokerClient):**
    - **The Source of Truth.** Do NOT edit `core/client.py` (Deprecated).
    - Wraps `ShoonyaApiPy`.
    - Manages `SYMBOLDICT` (Live Data).
    - Delegated Logic:
        - `master/`: Loads Scrip Masters and Custom Maps.
        - `executor/`: Handles Order Placement logic.
        - `resolver/`: Resolves Symbols (Future/Option chains).

3.  **`core/engine/executor.py`:**
    - Consumes signals.
    - Routes orders:
        - `MCX`: Calls `place_future_order`.
        - `NFO`: Calls `place_credit_spread`.

## 🧠 Critical Logic: MCX Token Resolution

We faced persistent `future_not_found` errors because `place_future_order` was receiving prefixed tokens (`MCX|477167`) but the map only contained raw IDs (`477167`), or vice-versa.

**The Fix:** "Dual-Key" Strategy in `ScripMaster.load_segment_futures_map`.
- We store **both** versions in `TOKEN_TO_SYMBOL`.
    - `'477167': 'COPPER27FEB26'`
    - `'MCX|477167': 'COPPER27FEB26'`

**The Fix:** Priority Lot Size Lookup in `BrokerClient.place_future_order`.
1.  **Priority 0:** Check `SYMBOLDICT` (Live WS). If the feed is live, it contains the authoritative `ls` (Lot Size).
2.  **Priority 1:** Check `TOKEN_TO_LOTSIZE` (Memory Cache). Populated from `mcx_futures_map.json` at startup.
3.  **Priority 2:** Check `DERIVATIVE_OPTIONS` (Master File).

## 🛠️ Utilities
- `utils/mcx/update_mcx_config.py`:
    - Connects to Shoonya.
    - Finds nearest futures.
    - **Captures Lot Size** and saves to `data/mcx_futures_map.json`.
    - Updates `config/mcx/config.py` with the universe list.

## ⚠️ Gotchas
- **`core/client.py` is DEPRECATED.** It is a monolithic legacy file. Do not edit it. The active code is in `core/broker/`.
