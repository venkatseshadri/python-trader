# 📊 Google Sheets Integration

## Overview
ORBITER offloads all UI and Logging duties to Google Sheets. This allows you to monitor the bot from your phone without needing a custom frontend.

## Setup
1.  **GCP Console**: Create a Service Account and download the JSON key.
2.  **File Placement**: Save the key as `orbiter/bot/credentials.json`.
3.  **Sharing**: Share your Target Sheet with the Service Account email address.

## Data Structure
The bot expects (or creates) the following tabs:

### 1. `active_positions`
Real-time dashboard. Cleared when trades exit.
- **Columns**: `Symbol`, `Strategy`, `Entry Price`, `LTP`, `PnL %`, `PnL ₹`.

### 2. `trade_logs`
Permanent history.
- **Columns**: `Entry Time`, `Exit Time`, `Symbol`, `Result`, `Reason`.

### 3. `scan_metrics`
Debug view showing internal scores.
- **Columns**: `Token`, `ORB Score`, `EMA Score`, `Total Score`.

## Latency
Updates are batched and pushed every **60 seconds** to avoid hitting Google API rate limits.
