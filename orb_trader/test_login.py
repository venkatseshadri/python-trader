#!/usr/bin/env python3
import sys
import os
# Fix: Add ShoonyaApi-py to path (api_helper.py location)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.getcwd())))

import yaml
from core.shoonya_client import ShoonyaWebSocketClient
import logging

logging.basicConfig(level=logging.INFO)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")  

def main():
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)
        print("✅ Config loaded:", list(config['shoonya'].keys()))
    
    # Test Shoonya login
    ws = ShoonyaWebSocketClient(config)
    
    if ws.login():
        print("✅ Shoonya login SUCCESS!")
        print("🚀 Ready for WebSocket test")
    else:
        print("❌ Shoonya login FAILED - check config.yaml credentials")
        print("Expected keys: user_id, password, api_key")

if __name__ == "__main__":
    main()
