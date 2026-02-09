import sys
import os
from typing import Dict, Optional, Callable
import logging
import time

# Add ShoonyaApi-py to path for api_helper import
shoonya_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ShoonyaApi-py')
sys.path.insert(0, shoonya_path)

from api_helper import ShoonyaApiPy

class ShoonyaWebSocketClient:
    def __init__(self, config: Dict):
        self.api = ShoonyaApiPy()
        self.config = config
        self.ltp_cache = {}
        
def login(self) -> bool:
    try:
        # Map your config keys → Shoonya API parameter names
        login_params = {
            'userid': self.config['shoonya']['user_id'],
            'password': self.config['shoonya']['password'],
            'twoFA': self.config['shoonya']['factor2'],  # DOB/PAN/TOTP
            'vendor_code': self.config['shoonya']['vendor_code'],
            'api_secret': self.config['shoonya']['api_key'],
            'imei': self.config['shoonya']['imei']
        }
        
        ret = self.api.login(**login_params)
        logging.info("✅ Shoonya login success")
        return ret is not None
    except Exception as e:
        logging.error(f"❌ Login failed: {e}")
        return False

    
    def start_websocket(self, ltp_callback):
        def feed_update(tick):
            token = tick.get('tk', tick.get('ts'))  # PDF field names
            ltp = float(tick.get('lp', 0))
            symbol = self._token_to_symbol(token)
            if symbol:
                ltp_callback(symbol, ltp)
                print(f"LTP: {symbol} = {ltp}")
        
        def socket_open():
            print("🔥 WebSocket LIVE")
            # Auto-subscribe top stocks
            self.api.subscribe(['NSE|26000'])  # RELIANCE
        
        self.api.start_websocket(
            subscribe_callback=feed_update,
            socket_open_callback=socket_open
        )
