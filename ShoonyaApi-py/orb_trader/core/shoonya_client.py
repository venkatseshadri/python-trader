import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))  # ShoonyaApi-py

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
