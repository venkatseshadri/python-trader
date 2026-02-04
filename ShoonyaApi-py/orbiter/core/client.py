#!/usr/bin/env python3
"""
ORBITER BrokerClient - Production Shoonya API Wrapper
VENKAT SESHADRI | FA333160 | LIVE Feb 2026
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api_helper import ShoonyaApiPy
import yaml
import logging
import time
from typing import Dict, Optional, Any

class BrokerClient:
    """
    Production Shoonya API client for ORBITER trading strategies
    LIVE: RELIANCE ₹1455, NTPC ₹362, VIPIND ₹373
    """
    
    def __init__(self, config_path: str = '../cred.yml'):
        self.api = ShoonyaApiPy()
        self.socket_opened = False
        self.SYMBOLDICT: Dict[str, Dict[str, Any]] = {}
        
        # Load credentials
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_file = os.path.join(project_root, config_path)
        with open(config_file) as f:
            self.cred = yaml.load(f, Loader=yaml.FullLoader)
            
        logging.basicConfig(level=logging.DEBUG)
        print(f"🚀 BrokerClient initialized: {self.cred['user']}")
    
    def login(self) -> bool:
        """Login with TOTP (update cred.yml every 30s)"""
        print("🔐 Authenticating...")
        ret = self.api.login(
            userid=self.cred['user'],
            password=self.cred['pwd'],
            twoFA=self.cred['factor2'],  # Google Authenticator
            vendor_code=self.cred['vc'],
            api_secret=self.cred['apikey'],
            imei=self.cred['imei']
        )
        return bool(ret)
    
    def start_live_feed(self, symbols: list = None):
        """Start WebSocket with your trading symbols"""
        if symbols is None:
            symbols = ['NSE|2885', 'NSE|11630', 'NSE|3703']  # RELIANCE, NTPC, VIPIND
            
        def quote_callback(message):
            """LIVE quote handler (ts safety fixed)"""
            if 'ts' not in message or 'lp' not in message:
                return
                
            key = f"{message['e']}|{message['tk']}"
            self.SYMBOLDICT[key] = message
            print(f"📊 LIVE: {message['ts']} ₹{message['lp']}")
        
        def open_callback():
            """Auto-subscribe on connect"""
            self.socket_opened = True
            print("🚀 WEBSOCKET LIVE!")
            self.api.subscribe(symbols, feed_type='d')
            print(f"✅ Subscribed {len(symbols)} symbols")
        
        def order_callback(message):
            """Live order tracking"""
            print(f"📋 ORDER: {message.get('status')} {message.get('tsym')}")
        
        self.api.start_websocket(
            order_update_callback=order_callback,
            subscribe_callback=quote_callback,
            socket_open_callback=open_callback
        )
    
    def get_ltp(self, exch_token: str) -> Optional[float]:
        """Get LIVE LTP by exchange|token"""
        data = self.SYMBOLDICT.get(exch_token, {})
        return float(data.get('lp', 0)) if data else None
    
    def get_volume(self, exch_token: str) -> Optional[int]:
        """Get LIVE volume"""
        data = self.SYMBOLDICT.get(exch_token, {})
        return int(data.get('v', 0)) if data else None
    
    # YOUR TRADING SYMBOLS (hardcoded for speed)
    @property
    def reliance_ltp(self) -> float:
        return self.get_ltp('NSE|2885')
    
    @property
    def ntpc_ltp(self) -> float:
        return self.get_ltp('NSE|11630')
    
    @property
    def vipind_ltp(self) -> float:
        return self.get_ltp('NSE|3703')
    
    def close(self):
        """Clean shutdown"""
        if self.socket_opened:
            self.api.close_websocket()
            print("🔌 Connection closed")
