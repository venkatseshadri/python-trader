# 🚀 Deployment & Release Guide

> Complete guide for deploying code changes from development to production

This document provides step-by-step instructions for developers, CI/CD bots, and agents to understand the complete deployment pipeline.

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [GitHub Actions CI/CD](#github-actions-cicd)
4. [Development Workflow](#development-workflow)
5. [Step-by-Step Deployment](#step-by-step-deployment)
6. [Server Deployment](#server-deployment)
7. [Health Check & Monitoring](#health-check--monitoring)
8. [Troubleshooting](#troubleshooting)

---

## 🏗 Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Development    │     │     GitHub      │     │   Production    │
│  (Local VM)     │────▶│   Repository    │────▶│    Server       │
│                 │     │                 │     │                 │
│  - Code edits   │     │  - Version      │     │  - Binary runs  │
│  - Test locally │     │    control      │     │  - Health check │
│  - Build binary │     │  - Release tags │     │  - Cron jobs    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Source Code | `/home/trading_ceo/python-trader/` | Python trading bot |
| Built Binary | `/home/trading_ceo/python-trader/dist/orbiter-X.X.X` | Standalone executable |
| Git Remote | `git@github.com:venkatseshadri/python-trader.git` | Code repository |
| Production Scripts | `/home/trading_ceo/*.sh` | Deployment & cleanup scripts |
| Health Check | `/home/trading_ceo/health_check.sh` | Auto-restart mechanism |

---

## 🦸 GitHub Actions CI/CD

The project includes automated CI/CD workflows in `.github/workflows/`:

### Workflow Files

| File | Purpose |
|------|---------|
| `ci.yml` | Main workflow: runs tests + builds binary on push |
| `test.yml` | Dedicated test runner with linting |

### What CI Does Automatically

1. **On Push/PR**: Runs all unit tests (skips broker tests)
2. **On Push to Main**: Builds the binary
3. **On Tag**: Creates a GitHub Release with the binary

### CI Status

```
✅ Tests run automatically (140 tests, no broker needed)
✅ Binary builds on main branch push
✅ Artifacts uploaded for download
```

### Manual Run

To trigger workflows manually:
- Go to: https://github.com/venkatseshadri/python-trader/actions
- Click workflow → "Run workflow"

### CI Test Results

| Metric | Value |
|--------|-------|
| Tests Passed | 140 |
| Tests Skipped | 94 (require broker) |
| Tests Failed | 0 |

> **Note**: CI runs without broker access. Tests use captured data or mocks. See [TEST_DATA_CAPTURE_COMPLETE.md](./TEST_DATA_CAPTURE_COMPLETE.md).

---

## ✅ Prerequisites

### For Development Machine

1. **Python 3.10+** installed
2. **PyInstaller** for building binaries:
   ```bash
   pip install pyinstaller
   ```
3. **Git** configured with SSH keys for GitHub
4. **Access** to the production server (SSH)

### For Production Server

1. **Python 3.10+** (for health check script only)
2. **Git** installed
3. **SSH access** to the server
4. **Crontab** configured for health checks

---

## 🔄 Development Workflow

### Option A: Full Deployment (Recommended)

```
1. Make code changes
2. Test locally
3. Build binary
4. Push to GitHub
5. SSH to server
6. Pull latest code
7. Deploy new binary
8. Verify & monitor
```

### Option B: Quick Fix (Emergency)

```
1. Make code changes directly on server
2. Test/verify
3. Push to GitHub (to sync)
4. Document the change
```

---

## 📦 Step-by-Step Deployment

### Step 1: Make Code Changes

Edit files in `/home/trading_ceo/python-trader/`:

```bash
# Example: Edit a strategy file
vim /home/trading_ceo/python-trader/orbiter/strategies/nfo.py

# Or use your preferred editor
code /home/trading_ceo/python-trader/
```

### Step 2: Test Locally (Optional but Recommended)

```bash
cd /home/trading_ceo/python-trader

# Run with a test strategy
python orbiter/main.py --strategyCode=test

# Run tests - no broker needed (uses captured data or mocks)
python -m pytest orbiter/tests/ -v
```

#### Test Data Capture System
Tests can run offline without broker connection using captured data:

```bash
# First time: Capture live broker data (requires login)
python3 orbiter/tests/capture_test_data.py

# Subsequent runs: No broker needed
python -m pytest orbiter/tests/ -v
```

> 📖 See [TEST_DATA_CAPTURE_COMPLETE.md](./TEST_DATA_CAPTURE_COMPLETE.md) for complete documentation.

### Step 3: Build the Binary

```bash
cd /home/trading_ceo/python-trader

# Run the build script
./build.sh
```

**What happens:**
- PyInstaller compiles Python code into a standalone executable
- Binary is created at `dist/orbiter-X.X.X` (version from `version.txt`)
- SHA256 checksum generated

**Output:**
```
✅ Build complete!
   Binary: dist/orbiter-4.6.1
   Size: 70M
```

### Step 4: Push to GitHub

```bash
cd /home/trading_ceo/python-trader

# Check status
git status

# Add changes
git add -A

# Commit with message
git commit -m "Fix: Updated health_check.sh to use binary instead of Python"

# Push to remote
git push origin main
```

**Important:** Always push AFTER building so the binary version matches the code!

---

## 🖥 Server Deployment

### Step 5: SSH to Production Server

```bash
ssh trading_ceo@<server-ip>
# or
ssh trading_ceo@your-server-hostname
```

### Step 6: Pull Latest Code

```bash
cd /home/trading_ceo/python-trader

# Pull latest changes
git pull origin main

# Verify the binary exists
ls -la dist/
```

### Step 7: Deploy New Binary

The server has a specific binary filename hardcoded in scripts. Check current version:

```bash
# Check what binary is currently configured
grep "orbiter-" /home/trading_ceo/health_check.sh

# Update if version changed
# Example: If you built orbiter-4.6.2, update:
sed -i 's/orbiter-4.6.1/orbiter-4.6.2/' /home/trading_ceo/health_check.sh
```

### Step 8: Copy Binary to Production Location

```bash
# The dist folder is in python-trader, which is pulled from git
# Just ensure the new binary is there
ls -la /home/trading_ceo/python-trader/dist/
```

---

## ❤️ Health Check & Monitoring

### Understanding the Health Check

The server uses a **cron job** to run `health_check.sh` every 5 minutes:

```bash
# Check cron jobs
crontab -l
```

**How it works:**
1. Cron runs `health_check.sh <strategyCode>` (e.g., `n1`, `m1`)
2. Script checks if a process with that strategy is running
3. If NOT running → starts the binary
4. If running → does nothing

### Key Files on Server

| File | Purpose |
|------|---------|
| `/home/trading_ceo/health_check.sh` | Restarts orbiter if not running |
| `/home/trading_ceo/cleanup_*.sh` | Kill running processes |
| `/tmp/orbiter_*.log` | Log files for each strategy |
| `/home/trading_ceo/python-trader/dist/orbiter-X.X.X` | The actual binary |

### Manual Health Check

```bash
# Check if strategy is running
pgrep -f "strategyCode=n1"

# Manually run health check
/home/trading_ceo/health_check.sh n1

# View logs
tail -f /tmp/orbiter_n1.log
```

### Cleanup Scripts

| Script | Purpose |
|--------|---------|
| `/home/trading_ceo/cleanup_bfo.sh` | Kill BFO strategy processes |
| `/home/trading_ceo/cleanup_nfo.sh` | Kill NFO strategy processes |
| `/home/trading_ceo/cleanup_mcx.sh` | Kill MCX strategy processes |
| `/home/trading_ceo/cleanup_weekly.sh` | Clean old log files |

---

## 🔧 Troubleshooting

### Binary Not Found

```bash
# Error: nohup: can't execute '/home/trading_ceo/python-trader/dist/orbiter-X.X.X': No such file or directory

# Fix: Check if binary exists
ls -la /home/trading_ceo/python-trader/dist/

# If not, pull latest and rebuild
git pull origin main
./build.sh
```

### Version Mismatch

```bash
# Error: Wrong binary version used

# Fix: Update health_check.sh with correct version
vim /home/trading_ceo/health_check.sh
# Change: orbiter-4.6.1 → orbiter-4.6.2
```

### Process Not Starting

```bash
# Check logs
tail -50 /tmp/orbiter_n1.log

# Check permissions
ls -la /home/trading_ceo/python-trader/dist/orbiter-*

# Make executable if needed
chmod +x /home/trading_ceo/python-trader/dist/orbiter-*
```

### Git Push Failed

```bash
# Check remote
git remote -v

# Verify SSH keys are added to GitHub
ssh -T git@github.com
```

---

## 📝 Quick Reference Card

### One-Line Deployment Summary

```bash
# Development machine:
cd /home/trading_ceo/python-trader && git add -A && git commit -m "Your changes" && git push origin main

# CI automatically:
#   1. Runs tests (140 passed)
#   2. Builds binary
#   3. Uploads artifact

# Server (after push):
cd /home/trading_ceo/python-trader && git pull origin main

# Verify binary version matches
ls /home/trading_ceo/python-trader/dist/orbiter-*
```

### Common Commands

| Action | Command |
|--------|---------|
| Build binary | `./build.sh` |
| Push to repo | `git push origin main` |
| Pull on server | `git pull origin main` |
| Check running | `pgrep -af orbiter` |
| View logs | `tail -f /tmp/orbiter_n1.log` |
| Force restart | `/home/trading_ceo/cleanup_nfo.sh && /home/trading_ceo/health_check.sh n1` |

---

## 🔄 For CI/CD Bots & Agents

If you're automating this process:

1. **Always use the binary**, never run `python orbiter/main.py` directly
2. **Version control**: The binary filename contains the version (e.g., `orbiter-4.6.1`)
3. **Update health_check.sh** if the binary version changes
4. **Check logs** after deployment: `/tmp/orbiter_<strategy>.log`
5. **Verify with health check**: Run `/home/trading_ceo/health_check.sh <strategy>` after deployment

---

## 📞 Support

- **GitHub Issues**: https://github.com/venkatseshadri/python-trader/issues
- **Documentation**: See `/home/trading_ceo/python-trader/docs/`

---

*Last Updated: 2026-03-23*
*Maintained by: Trading Team*
