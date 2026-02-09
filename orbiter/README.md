# ORBITER

[![Status][status-badge]][status-link] [![Python][python-badge]][python-link] [![License][license-badge]][license-link]

**ORBITER** - NIFTY50 ORB Top-10 Options Trading Framework

Scans all 50 NIFTY stocks for 9:15-9:30 ORB breakouts, ranks by momentum strength, trades Top 10 via current-week options with websocket SL monitoring.

## 🚀 Features

- **NIFTY50 Universe** → Dynamic Top-10 ORB selection
- **Shoonya API** → REST (orders) + Websocket (quotes + order updates)
- **Plug-in Architecture** → Swap strategies via config only
- **Live SL/Target** → Option premium-based stops/targets via touchline feed
- **Simulation Mode** → Dry-run with real market data
- **Production Ready** → Logging, error handling, clean shutdown

## 📁 Architecture

orbiter/
├── config/ # Universe + strategy params
├── core/ # Broker client + execution engine
├── strategies/ # ORB logic + future variants
├── data/ # NIFTY50 symbols + masters
├── logs/ # Runtime logs
└── main.py # Generic runner


## 🎯 How It Works

1. Scan NIFTY50 (9:15-9:30 ORB high/low via REST)
2. Current LTP → Direction + Distance from ORB edge
3. Rank by ORB Distance → Top 10 strongest breakouts
4. Map to Current Week CE/PE options
5. Market Entry → Websocket SL monitoring (30% option premium)


## 🛠 Quick Start

```bash
# 1. Clone & setup
git clone <repo>
cd orbiter
pip install -r requirements.txt

# 2. Add credentials
cp cred.yml.example cred.yml
# Edit cred.yml with your Shoonya details

# 3. Run simulation
python run_orbiter.py

# 4. Go live (edit config.py → simulate=False)
python run_orbiter.py

⚙️ Configuration
Single file controls everything:

# config/config.py
STRATEGY_NAME = "ORB_NIFTY50_TOP10"
UNIVERSE["symbols"] = ["RELIANCE-EQ", "HDFCBANK-EQ", ...]  # Full NIFTY50
STRATEGIES["ORB_NIFTY50_TOP10"]["params"]["top_n"] = 10
STRATEGIES["ORB_NIFTY50_TOP10"]["params"]["option_sl_pct"] = 0.30

📊 Strategy Flow
NIFTY50 (50 stocks)
    ↓ REST: get_candles(9:15-9:30)
    ↓ Compute ORB hi/lo + LTP direction
    ↓ Filter breakouts + sort by distance
    ↓ Top 10 → Map to options (CE/PE)
    ↓ REST: Market entry orders
    ↓ WS: Subscribe option tokens
    ↓ WS: Live SL monitoring (30% premium)

🔧 Core Components
Module	Purpose	Reusable
core/client.py	Shoonya REST+WS	✅ Any broker
core/sl_manager.py	SL/Target engine	✅ Any strategy
core/executor.py	Entry + wiring	✅ Any options
strategies/orb_strategy.py	NIFTY50→Top10 logic	❌ Strategy-specific
📈 Example Trade Plan
text
RELIANCE-EQ: LTP=2850, ORB_hi=2845 → CE option → Rank #1
HDFCBANK-EQ: LTP=1520, ORB_lo=1535 → PE option → Rank #3
→ 10 total legs executed + monitored
🚀 Future Strategies (Config Only)
text
SIDEWAYS_NIFTY50 → Short strangles on range-bound
MOMENTUM_TOP10 → EMA crossover on F&O stocks
BANKNIFTY_ORB → Scale to BankNifty universe
📋 Requirements
text
ShoonyaApi-py>=1.0.0
pyyaml>=6.0
pandas>=2.0
numpy>=1.24
🔒 Credentials
cred.yml (never commit):

text
user: your_userid
pwd: your_password
vc: your_vendor_code
apikey: your_api_key
factor2: your_2fa
imei: your_imei
🛡️ Simulation Mode
python
# config.py
client = BrokerClient(cred_path="cred.yml", simulate=True)
# Real WS feed + fake orders → Full P&L simulation
📊 Logging
text
logs/orbiter.log → All trades, WS events, SL triggers
Real-time console → Entry/exit confirmations
🧪 Testing
bash
pip install pytest
pytest tests/
📄 License
MIT License - Free to use/modify.

🙏 Acknowledgments
Built for Indian options traders using Shoonya API. Inspired by ORB momentum concepts.

ORBITER: Find the strongest ORB among NIFTY50. Trade the Top 10. Let websocket SL do the rest.

Version 1.0 - Feb 2026