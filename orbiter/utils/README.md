# Market Utilities

Maintenance scripts for keeping your configurations and contract mappings fresh.

## Segmented Utilities

### `nfo/` (Equity Derivatives)
*   **`update_futures_config.py`**:
    *   Scans the NIFTY 50 universe.
    *   Resolves current near-month Future contracts.
    *   Updates `config/nfo/exchange_config.py` with fresh tokens.
    *   Saves a local mapping to `data/nfo_futures_map.json`.

### `mcx/` (Commodities)
*   **`update_mcx_config.py`**:
    *   Scans the defined MCX symbols (Crude, Gold, Silver, etc.).
    *   Resolves current near-month Commodity Future contracts.
    *   Updates `config/mcx/exchange_config.py` with fresh tokens.
    *   Saves a local mapping to `data/mcx_futures_map.json`.

## Automation
The core bot (`BrokerClient`) will automatically attempt to run these utilities if it detects that the local contract mappings have expired.
