import os
import sys
import yaml
import logging
from typing import Dict, Optional, Any, List

# Add ShoonyaApi-py to path
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
shoonya_path = os.path.join(os.path.dirname(base_dir), 'ShoonyaApi-py')
sys.path.insert(0, shoonya_path)

from api_helper import ShoonyaApiPy

class ConnectionManager:
    def __init__(self, config_path: str = '../cred.yml'):
        self.api = ShoonyaApiPy()
        self.socket_opened = False
        
        # Load credentials
        orbiter_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.config_file = os.path.abspath(os.path.join(orbiter_root, config_path))
        with open(self.config_file) as f:
            self.cred = yaml.load(f, Loader=yaml.FullLoader)
            
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("urllib3").setLevel(logging.INFO)
        logging.getLogger("websocket").setLevel(logging.INFO)
        print(f"🚀 BrokerClient Connection Initialized: {self.cred['user']}")

    def login(self, factor2_override: Optional[str] = None) -> bool:
        print("🔐 Authenticating...")
        try:
            current = self.cred.get('factor2', '')
            new2 = (factor2_override or "").strip()
            if not new2:
                new2 = input(f"Enter 2FA (current: {current}) or press Enter to keep: ").strip()
            if new2:
                self.cred['factor2'] = new2
                with open(self.config_file, 'w') as f:
                    yaml.dump(self.cred, f)
                print(f"🔒 Updated 2FA in {self.config_file}")
        except Exception: pass

        ret = self.api.login(
            userid=self.cred['user'],
            password=self.cred['pwd'],
            twoFA=self.cred['factor2'],
            vendor_code=self.cred['vc'],
            api_secret=self.cred['apikey'],
            imei=self.cred['imei']
        )
        if not ret or str(ret.get('stat', '')).lower() != 'ok':
            reason = ret.get('emsg') or ret.get('reason') if isinstance(ret, dict) else ''
            print(f"❌ Login failed{': ' + reason if reason else ''}")
            return False
        return True

    def start_live_feed(self, symbols: List[str], on_tick_callback, verbose=False):
        print(f"🚀 Starting WS for {len(symbols)} symbols...")
        
        token_to_exch = {}
        for s in symbols:
            if '|' in s:
                ex, tk = s.split('|')
                token_to_exch[tk] = ex

        def on_tick(message):
            if 'lp' not in message: return
            token = str(message.get('tk', ''))
            exch = token_to_exch.get(token) or message.get('e', 'NSE')
            on_tick_callback(message, token, exch)
        
        def on_open():
            self.socket_opened = True
            print("🚀 WEBSOCKET LIVE!")
            self.api.subscribe(symbols, feed_type='d')
        
        self.api.start_websocket(
            subscribe_callback=on_tick,
            socket_open_callback=on_open,
            order_update_callback=lambda x: print("📋 ORDER:", x)
        )

    def close(self):
        if self.socket_opened:
            self.api.close_websocket()
            print("🔌 Connection closed")
