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

## 4) Run

```bash
./scripts/run.sh
```

Simulation mode:

```bash
./scripts/run.sh --simulation
```

## Notes

- TA-Lib is built from source during install.
- The virtualenv is created at .venv/ in the repo root.
