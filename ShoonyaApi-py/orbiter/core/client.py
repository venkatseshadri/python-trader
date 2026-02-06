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
    
    def start_live_feed(self, symbols: list): 
        print(f"🚀 Starting WS for {len(symbols)} symbols...")
        self.symbols = symbols
        
        # Official ShoonyaApiPy syntax (from docs)
        def on_tick(message):
            if 'ts' not in message or 'lp' not in message: return
            key = f"{message['e']}|{message['tk']}"
            self.SYMBOLDICT[key] = message
            print(f"📊 LIVE: {message['ts']} ₹{message['lp']}")
        
        def on_open():
            self.socket_opened = True
            print("🚀 WEBSOCKET LIVE!")
            self.api.subscribe(symbols, feed_type='d')
        
        self.api.start_websocket(
            subscribe_callback=on_tick,
            socket_open_callback=on_open,
            order_update_callback=lambda x: print("ORDER:", x)
        )

            
    def quote_callback(self, message):
        if 'ts' not in message or 'lp' not in message:
            return
        key = f"{message['e']}|{message['tk']}"
        self.SYMBOLDICT[key] = message
        print(f"📊 LIVE: {message['ts']} ₹{message['lp']}")

    
    def open_callback(self):
        self.socket_opened = True
        print("🚀 WEBSOCKET LIVE!")
        self.api.subscribe(self.symbols, feed_type='d')  # ← 'symbols' also undefined
    
    def order_callback(message):
        """Live order tracking"""
        print(f"📋 ORDER: {message.get('status')} {message.get('tsym')}")
    
    def start_websocket(self):
        def on_feed(tick):
            print("FEED:", tick)  # Test callback
            
        self.api.start_websocket(
            subscribecallback=on_feed,
            orderupdatecallback=lambda order: print("ORDER:", order)
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
