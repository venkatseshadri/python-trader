# 📱 Project: Remote Control & Monitoring

## Goal
Establish a triple-redundant system for 24/7 autonomous operation on remote hardware (Raspberry Pi or Cloud Workers).

## 🏗 Proposed Architecture
- **Tier 1: Process Management (PM2)**
  - Auto-restart on failure.
  - Log rotation to prevent disk overflow.
- **Tier 2: Command & Control (Telegram Bot)**
  - Command: `/status` - Get current P&L and active positions.
  - Command: `/kill` - Emergency square-off and stop bot.
  - Command: `/reboot` - Restart the trading process.
- **Tier 3: Dynamic Config (Google Sheets)**
  - A dedicated "Control Panel" tab to update Stop Loss % or Lot Sizes in real-time.

## 📅 Roadmap
1. [ ] Implement PM2 process configuration.
2. [ ] Develop `orbiter_remote.py` Telegram listener.
3. [ ] Integrate dynamic config polling in the main loop.
