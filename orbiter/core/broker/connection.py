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

try:
    import pyotp
except ImportError:
    pyotp = None

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
        
        two_fa = ""
        # 1. Priority: Manual override
        if factor2_override:
            two_fa = factor2_override.strip()
        
        # 2. Priority: Automated TOTP (Best for Service/Daemon)
        elif self.cred.get('totp_key'):
            if pyotp:
                try:
                    totp = pyotp.TOTP(self.cred['totp_key'].replace(" ", ""))
                    two_fa = totp.now()
                    print(f"🤖 Automated TOTP generated")
                except Exception as e:
                    print(f"⚠️ TOTP generation failed: {e}")
            else:
                print("⚠️ 'pyotp' not installed. Cannot generate TOTP.")

        # 3. Priority: Interactive Input (Fallback)
        if not two_fa:
            try:
                current = self.cred.get('factor2', '')
                two_fa = input(f"Enter 2FA (current: {current}) or press Enter to keep: ").strip()
                if not two_fa:
                    two_fa = current
            except (EOFError, RuntimeError):
                # Running in non-interactive environment (service)
                two_fa = self.cred.get('factor2', '')
                if not two_fa:
                    print("❌ No 2FA provided and environment is non-interactive.")
                    return False

        if two_fa:
            self.cred['factor2'] = two_fa
            # Update local credentials file if it changed
            try:
                with open(self.config_file, 'w') as f:
                    yaml.dump(self.cred, f)
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
        
        # 🔥 NUCLEAR FIX (v3.14.9)
        # Manually inject mangled private attributes to ensure all internal API calls (like get_positions)
        # always find the credentials regardless of how the object was initialized.
        setattr(self.api, '_NorenApi__username', self.cred['user'])
        setattr(self.api, '_NorenApi__accountid', self.cred['user'])
        
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
            # 🔥 NEW: Subscribe to live order status updates (v3.15.9)
            self.api.subscribe_orders()
        
        self.api.start_websocket(
            subscribe_callback=on_tick,
            socket_open_callback=on_open,
            order_update_callback=lambda x: print("📋 ORDER:", x)
        )

    def close(self):
        if self.socket_opened:
            self.api.close_websocket()
            print("🔌 Connection closed")
