# Configuration Directory

This directory contains the hierarchical configuration system for the Orbiter trading bot.

## Hierarchy

1.  **`main_config.py` (The Strategy Layer)**:
    *   Contains shared logic parameters that define **how** the bot trades.
    *   *Parameters*: `ENTRY_WEIGHTS`, `TRADE_SCORE`, `TARGET_PROFIT_RS`, `TSL_RETREACEMENT_PCT`, etc.
2.  **`exchange_config.py` (The Segment Layer)**:
    *   Specific to a market (NFO or MCX).
    *   Contains "Market Plumbing" details.
    *   *Parameters*: `MARKET_OPEN/CLOSE`, `SYMBOLS_FUTURE_UNIVERSE`, `EXECUTION_MODE` (`CREDIT_SPREAD` or `FUTURES`).

## Segment Mapping

| Segment | Path | Execution Mode | Instrument |
| :--- | :--- | :--- | :--- |
| **NFO** | `config/nfo/exchange_config.py` | `CREDIT_SPREAD` | `OPTSTK` |
| **MCX** | `config/mcx/exchange_config.py` | `FUTURES` | `OPTCOM` |

## Usage
The `main.py` runner automatically merges the layers at runtime into a single `full_config` dictionary based on the current IST time.
