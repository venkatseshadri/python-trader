#!/bin/bash
# orbiter/switch.sh - Switch orbiter strategy and trading mode

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 <strategy_code> [options]"
    echo ""
    echo "Arguments:"
    echo "  strategy_code    Strategy to run (e.g., n1, n2, m1, s1)"
    echo ""
    echo "Options:"
    echo "  --paper=false   Enable live trading (default: true for paper trading)"
    echo "  --sim=false     Disable market hours simulation (default: true)"
    echo ""
    echo "Examples:"
    echo "  $0 n1                    # Paper trade, with market hours simulation"
    echo "  $0 n1 --paper=false     # Live trading, with market hours simulation"
    echo "  $0 n2 --paper=false --sim=false  # Live trading, real market hours only"
    exit 1
}

# Parse arguments
if [ $# -lt 1 ]; then
    usage
fi

STRATEGY=$1
shift || true

PAPER_TRADE=true
SIMULATE_HOURS=true

# Parse options
for arg in "$@"; do
    case $arg in
        --paper=false)
            PAPER_TRADE=false
            ;;
        --paper=true)
            PAPER_TRADE=true
            ;;
        --sim=false)
            SIMULATE_HOURS=false
            ;;
        --sim=true)
            SIMULATE_HOURS=true
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            usage
            ;;
    esac
done

# Validate strategy
case $STRATEGY in
    n1|n2|m1|m2|s1|s2)
        echo -e "${GREEN}Strategy: $STRATEGY${NC}"
        ;;
    *)
        echo -e "${RED}Invalid strategy: $STRATEGY${NC}"
        echo "Valid: n1, n2, m1, m2, s1, s2"
        exit 1
        ;;
esac

# Build service file
SERVICE_FILE="/etc/systemd/system/orbiter.service"

echo -e "${YELLOW}Creating orbiter.service...${NC}"

cat > $SERVICE_FILE << EOF
[Unit]
Description=ORBITER Trading Bot Daemon
After=network.target

[Service]
Type=simple
User=trader
Group=trader
WorkingDirectory=/home/trader/python-trader
Environment=PYTHONPATH=/home/trader/python-trader
$(if [ "$SIMULATE_HOURS" = "true" ]; then echo 'Environment=ORBITER_SIMULATE_MARKET_HOURS=true'; fi)

ExecStart=/home/trader/python-trader/.venv/bin/python3 orbiter/main.py --strategyCode=$STRATEGY --paper_trade=$PAPER_TRADE

Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}Service file created:${NC}"
cat $SERVICE_FILE

# Reload and restart
echo -e "${YELLOW}Reloading systemd and restarting orbiter...${NC}"
systemctl daemon-reload
systemctl restart orbiter

sleep 3

# Show status
echo ""
echo -e "${GREEN}Orbiter Status:${NC}"
systemctl status orbiter --no-pager | head -10
