# ORBITER v3.0: Remote Control & Monitoring Design

## 1. Architecture Overview
- **Tier 1: Process Management (PM2)**: For execution stability.
- **Tier 2: Command & Control (Telegram)**: For immediate action (Kill-switch).
- **Tier 3: Config Layer (Google Sheets)**: For dynamic parameter tuning.

## 2. Component Integration
- Bot script: orbiter_remote.py
- State file: data/current_state.json

*Design Document v1.0 | Feb 2026*
EOF
