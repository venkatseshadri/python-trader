# Configuration Directory

This directory contains all configuration files for the Orbiter trading bot.

## Structure

*   **`config.py`**: Contains shared global settings such as trade scores, weights, Rupee-based PnL targets, and trailing SL parameters.
*   **`nfo/`**: Contains equity derivative (Nifty 50) specific configuration.
    *   **`config.py`**: Symbols universe, market hours, and NSE-specific instrument types.
*   **`mcx/`**: Contains commodity specific configuration.
    *   **`config.py`**: Commodity symbols universe, evening market hours, and MCX-specific instrument types.

## Segment-Specific Constants

| Constant | NFO Segment | MCX Segment |
| :--- | :--- | :--- |
| **Market Open** | 9:15 AM IST | 9:00 AM IST |
| **Market Close** | 3:30 PM IST | 11:30 PM IST |
| **Option Instrument** | `OPTSTK` | `OPTCOM` |
