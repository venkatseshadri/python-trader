# Raspberry Pi Setup

## 1) Clone the project on the Pi

Option A: bootstrap script (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/venkatseshadri/python-trader/main/raspi_bootstrap.sh | bash
```

Option B: manual clone

```bash
git clone https://github.com/venkatseshadri/python-trader.git
cd python-trader
```

## 2) Install dependencies

```bash
./scripts/install.sh
```

## 3) Configure credentials

```bash
cp ShoonyaApi-py/cred.yml ShoonyaApi-py/cred.yml.bak
# edit ShoonyaApi-py/cred.yml with your credentials
```

## 4) Run as a Background Daemon (Recommended)

To run Orbiter 24/7 with automatic crash recovery and auto-switching between NFO and MCX sessions:

### A. Install the Service
```bash
# 1. Copy the service file
sudo cp install/rpi/orbiter.service /etc/systemd/system/

# 2. Setup the configuration file
cp install/rpi/orbiter.env /home/pi/python/

# 3. Reload and Enable
sudo systemctl daemon-reload
sudo systemctl enable orbiter
```

### B. Configure Runtime Mode
Edit `/home/pi/python/orbiter.env` to set the mode:
- `ORBITER_FLAGS=""` -> Live Production
- `ORBITER_FLAGS="--simulation"` -> Simulation Mode

### C. Control Commands
```bash
sudo systemctl start orbiter    # Start
sudo systemctl stop orbiter     # Stop
sudo systemctl restart orbiter  # Apply .env changes
sudo systemctl status orbiter   # Check Health
```

### D. Viewing Logs
- **Live Stream**: `sudo journalctl -u orbiter -f`
- **Session History**: Look in `logs/system/orbiter_YYYYMMDD_HHMM.log`

## 5) Manual Run

```bash
python orbiter/main.py
```

Simulation mode:

```bash
python orbiter/main.py --simulation
```

## Notes

- TA-Lib is built from source during install.
- The virtualenv is created at .venv/ in the repo root.
