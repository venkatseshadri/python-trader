import sys
import os

# Add ShoonyaApi-py to path for api_helper import
shoonya_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'ShoonyaApi-py')
sys.path.insert(0, shoonya_path)

from api_helper import ShoonyaApiPy
from typing import Dict, Optional, Callable
import logging
import time

class ShoonyaWebSocketClient:
    def __init__(self, config: Dict):
        self.api = ShoonyaApiPy()
        self.config = config
        self.ltp_cache = {}
        
    def login(self) -> bool:
        try:
            ret = self.api.login(**self.config['shoonya'])
            logging.info("✅ Shoonya login success")
            return ret is not None
        except Exception as e:
            logging.error(f"❌ Login failed: {e}")
            return False
    
    # ... rest of WebSocket methods
