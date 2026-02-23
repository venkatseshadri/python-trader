#!/bin/bash
# 🚀 ORBITER UNIFIED VPS BOOTSTRAP (v1.0)
# Purpose: One-click setup for high-performance trading & development.

echo "🛡️ Starting VPS Environment Setup..."

# 1. System Updates
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y build-essential wget git python3-pip python3-venv libatlas-base-dev htop sshpass

# 2. Install TA-Lib (C Library)
echo "📈 Installing TA-Lib C Library..."
if [ ! -f /usr/local/lib/libta_lib.a ]; then
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
    tar -xzf ta-lib-0.4.0-src.tar.gz
    cd ta-lib/
    ./configure --prefix=/usr
    make
    sudo make install
    cd ..
    rm -rf ta-lib*
fi

# 3. Project Environment
echo "📦 Setting up Python Virtual Environment..."
cd ~/python/python-trader
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install TA-Lib

# 4. Global Gemini CLI Config (Optional but recommended)
echo "🤖 Gemini CLI context ready for Unified Box."

echo "✅ VPS SETUP COMPLETE!"
echo "Run 'source .venv/bin/activate' to start."
