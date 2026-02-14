# 🐋 Orbiter Docker Installation

This directory contains the necessary configuration to run the Orbiter Trading Bot in a containerized environment. This is the recommended method for cloud deployments (Railway, DigitalOcean) or stable desktop execution.

## 🚀 Quick Start

### 1. Prerequisites
- Docker and Docker Compose installed.
- API credentials for Shoonya.

### 2. Configure Environment
Create a `.env` file in this directory (`docker/.env`) with your broker credentials:

```bash
# Shoonya Credentials
SHOONYA_USER=your_user_id
SHOONYA_PWD=your_password
SHOONYA_FACTOR2=your_totp_or_pin
SHOONYA_VC=your_vendor_code
SHOONYA_API_KEY=your_api_key
SHOONYA_IMEI=your_imei
```

### 3. Google Sheets Integration (Optional)
If using Google Sheets logging, ensure your `credentials.json` is placed in `python-trader/orbiter/bot/credentials.json`.

### 4. Run the Bot

**Simulation Mode (Safe for testing):**
```bash
docker-compose up orbiter-sim
```

**Live Mode:**
```bash
docker-compose up orbiter-live
```

## 🛠 Advanced Usage

### Build the image manually
From the **repository root**, run:
```bash
docker build -t orbiter -f docker/Dockerfile .
```

### View Logs
Logs are persisted to the host machine in `python-trader/orbiter/logs/` via Docker volumes.

---
*Containerized Trading | 2026*
