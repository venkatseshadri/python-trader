import os
import sys
import yaml
import logging
import base64
import hmac
import hashlib
import struct
import time
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

logger = logging.getLogger("ORBITER")

class ConnectionManager:
    @staticmethod
    def _generate_totp(secret: str, interval: int = 30, digits: int = 6) -> Optional[str]:
        """
        Generate TOTP from a base32 secret.
        Works even when `pyotp` is unavailable.
        """
        try:
            clean = (secret or "").replace(" ", "").upper()
            if not clean:
                return None
            key = base64.b32decode(clean, casefold=True)
            counter = int(time.time() // interval)
            msg = struct.pack(">Q", counter)
            digest = hmac.new(key, msg, hashlib.sha1).digest()
            offset = digest[-1] & 0x0F
            binary = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
            otp = binary % (10 ** digits)
            return str(otp).zfill(digits)
        except Exception:
            return None

    def __init__(self, config_path: str = '../cred.yml'):
        self.api = ShoonyaApiPy()
        self.socket_opened = False
        
        # Load credentials
        orbiter_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if os.path.isabs(config_path):
            self.config_file = config_path
        else:
            self.config_file = os.path.abspath(os.path.join(orbiter_root, config_path))
        with open(self.config_file) as f:
            self.cred = yaml.load(f, Loader=yaml.FullLoader)
            
        # 🔥 PRE-LOGIN NUCLEAR FIX: Inject username/account early
        setattr(self.api, '_NorenApi__username', self.cred['user'])
        setattr(self.api, '_NorenApi__accountid', self.cred['user'])

        # Enable internal library logging
        logging.getLogger("NorenRestApiPy").setLevel(logging.DEBUG)
        logging.getLogger("urllib3").setLevel(logging.DEBUG)
        logging.getLogger("websocket").setLevel(logging.DEBUG)
        
        print(f"🚀 BrokerClient Connection Initialized: {self.cred['user']}")

    def login(self, factor2_override: Optional[str] = None) -> bool:
        print("🔐 Authenticating...")
        
        two_fa = ""
        # 1. Priority: Manual override
        if factor2_override:
            two_fa = factor2_override.strip()
        elif os.environ.get("ORBITER_2FA"):
            two_fa = os.environ.get("ORBITER_2FA", "").strip()
        
        # 2. Priority: Automated TOTP (Best for Service/Daemon)
        elif self.cred.get('totp_key'):
            try:
                if pyotp:
                    totp = pyotp.TOTP(self.cred['totp_key'].replace(" ", ""))
                    two_fa = totp.now()
                else:
                    two_fa = self._generate_totp(self.cred.get('totp_key', '')) or ""
                if two_fa:
                    print("🤖 Automated TOTP generated")
                else:
                    print("⚠️ TOTP generation failed.")
            except Exception as e:
                print(f"⚠️ TOTP generation failed: {e}")

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

    def start_live_feed(self, symbols: List[Any], on_tick_callback, verbose=False):
        print(f"🚀 Starting WS for {len(symbols)} symbols...")
        
        token_to_exch = {}
        for s in symbols:
            if isinstance(s, dict):
                tk = str(s.get('token'))
                ex = s.get('exchange', 'NSE')
                token_to_exch[tk] = ex
            elif '|' in str(s):
                ex, tk = str(s).split('|')
                token_to_exch[tk] = ex

        def on_tick(message):
            if 'lp' not in message: 
                logger.debug(f"WS message ignored (no lp): {message}")
                return
            token = str(message.get('tk', ''))
            exch = token_to_exch.get(token) or message.get('e', 'NSE')
            logger.debug(f"WS tick for {token} ({exch})")
            on_tick_callback(message, token, exch)
        
        def on_open():
            self.socket_opened = True
            logger.info("🚀 WEBSOCKET LIVE!")
            # Ensure symbols are correctly prefixed for subscription
            formatted_symbols = []
            for s in symbols:
                if isinstance(s, dict):
                    tk = s.get('token')
                    ex = s.get('exchange', 'NSE')
                    formatted_symbols.append(f"{ex}|{tk}")
                elif '|' in str(s):
                    formatted_symbols.append(str(s))
                else:
                    formatted_symbols.append(f"NSE|{s}")
            
            logger.debug(f"Subscribing to: {formatted_symbols}")
            self.api.subscribe(formatted_symbols, feed_type='d')
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
