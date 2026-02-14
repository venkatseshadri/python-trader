# 📊 Historical Test Data Archive

This directory contains compressed historical market data used for data-driven strategy testing and regression validation.

## 📂 Contents

- **`nifty_50.zip`**: Contains `NIFTY 50_minute.csv` (SPOT data).
  - **Range**: Jan 2015 to July 2025.
  - **Resolution**: 1-minute OHLC.
  - **Note**: Volume data is not included/reliable for SPOT indices.

## 🛠 Usage in Tests

The test suite automatically searches for scenarios defined in `tests/data/scenario_data.json`. This ZIP file serves as the source of truth for extracting new scenarios when required.

To add a new scenario:
1. Unzip the file locally.
2. Identify the date/time range for the pattern (e.g. ORB, SL Hit).
3. Update `scenario_data.json` with the actual numbers.
