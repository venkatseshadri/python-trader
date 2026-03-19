import os
import sys
import yaml
import logging
import base64
import hmac
import hashlib
import struct
import time
import threading
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
    MAX_RECONNECT_ATTEMPTS = 10
    INITIAL_RECONNECT_DELAY = 1
    MAX_RECONNECT_DELAY = 60
    
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
        self._reconnect_attempts = 0
        self._reconnect_thread = None
        self._should_reconnect = True
        self._symbols_to_subscribe = []
        self._on_tick_callback = None
        self._pending_reconnect = False
        self.tick_handler = None
        
        # Load credentials - search multiple locations
        possible_creds = []
        
        if config_path:
            if os.path.isabs(config_path):
                possible_creds.append(config_path)
            else:
                # From orbiter root
                orbiter_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                possible_creds.append(os.path.abspath(os.path.join(orbiter_root, config_path)))
                # From project root
                project_root = os.path.dirname(orbiter_root)
                possible_creds.append(os.path.join(project_root, config_path.lstrip('../')))
                possible_creds.append(os.path.join(project_root, 'ShoonyaApi-py', config_path.lstrip('../')))
        
        # Add common credential file names
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        possible_creds.extend([
            os.path.join(project_root, 'ShoonyaApi-py', 'cred.shoonya.yml'),
            os.path.join(project_root, 'ShoonyaApi-py', 'cred.yml'),
            os.path.join(project_root, 'cred.shoonya.yml'),
            os.path.join(project_root, 'cred.yml'),
        ])
        
        # Find first existing cred file
        self.config_file = None
        for cred_file in possible_creds:
            if cred_file and os.path.exists(cred_file):
                self.config_file = cred_file
                break
        
        if not self.config_file:
            raise FileNotFoundError(f"Credentials file not found. Tried: {possible_creds}")
        
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

    def _is_session_expired(self, response) -> bool:
        """Check if response indicates session expired."""
        if isinstance(response, dict):
            stat = response.get('stat', '')
            if stat == 'Not_Ok':
                emsg = response.get('emsg', '')
                if 'session' in emsg.lower() or 'session' in str(emsg).lower():
                    return True
        return False

    def handle_api_call(self, api_method, *args, max_retries=2, **kwargs):
        """
        Wrapper for API calls that handles session expiry automatically.
        Returns (success, response) tuple.
        """
        for attempt in range(max_retries):
            try:
                response = api_method(*args, **kwargs)
                
                if self._is_session_expired(response):
                    if attempt < max_retries - 1:
                        logger.warning(f"🔑 Session expired. Re-authenticating (attempt {attempt + 1}/{max_retries})...")
                        if self.login():
                            logger.info(f"✅ Re-login successful. Retrying API call...")
                            continue
                    logger.error(f"❌ Session expired and re-authentication failed.")
                    return False, response
                return True, response
                
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"API call failed: {e}. Retrying...")
                    continue
                logger.error(f"API call failed after {max_retries} attempts: {e}")
                return False, None

    def start_live_feed(self, symbols: List[Any], on_tick_callback, verbose=False):
        logger.debug(f"[{self.__class__.__name__}.start_live_feed] - Starting live feed for {len(symbols)} symbols.")
        logger.debug(f"[{self.__class__.__name__}.start_live_feed] - Input symbols: {symbols[:3]}...")
        
        self._symbols_to_subscribe = symbols
        self._on_tick_callback = on_tick_callback
        
        token_to_exch = {}
        for s in symbols:
            if isinstance(s, dict):
                tk = str(s.get('token'))
                ex = s.get('exchange', 'NSE')
                token_to_exch[tk] = ex
                logger.debug(f"[{self.__class__.__name__}.start_live_feed] - Dict symbol: token={tk}, exchange={ex}")
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
            self._reconnect_attempts = 0
            logger.info("🚀 WEBSOCKET LIVE!")
            formatted_symbols = []
            for s in symbols:
                if isinstance(s, dict):
                    tk = s.get('token')
                    ex = s.get('exchange', 'NSE')
                    formatted_symbols.append(f"{ex}|{tk}")
                    logger.debug(f"[{self.__class__.__name__}.on_open] - Subscribing dict: {ex}|{tk}")
                elif '|' in str(s):
                    formatted_symbols.append(str(s))
                    logger.debug(f"[{self.__class__.__name__}.on_open] - Subscribing pipe: {str(s)}")
                else:
                    formatted_symbols.append(f"NSE|{s}")
                    logger.debug(f"[{self.__class__.__name__}.on_open] - Subscribing default: NSE|{s}")
            
            logger.debug(f"Subscribing to: {formatted_symbols}")
            self.api.subscribe(formatted_symbols, feed_type='d')
            self.api.subscribe_orders()
        
        def on_close():
            logger.warning(f"🔌 WebSocket closed. Attempting reconnect...")
            self.socket_opened = False
            self._schedule_reconnect()
        
        self.api.start_websocket(
            subscribe_callback=on_tick,
            socket_open_callback=on_open,
            socket_close_callback=on_close,
            order_update_callback=lambda x: print("📋 ORDER:", x)
        )

    def _schedule_reconnect(self):
        if not self._should_reconnect:
            return
        if self._reconnect_attempts >= self.MAX_RECONNECT_ATTEMPTS:
            logger.error(f"❌ Max reconnection attempts ({self.MAX_RECONNECT_ATTEMPTS}) reached. Giving up.")
            return
        if self._pending_reconnect:
            return
            
        self._pending_reconnect = True
        delay = min(self.INITIAL_RECONNECT_DELAY * (2 ** self._reconnect_attempts), self.MAX_RECONNECT_DELAY)
        self._reconnect_attempts += 1
        logger.info(f"⏳ Reconnecting in {delay}s (attempt {self._reconnect_attempts}/{self.MAX_RECONNECT_ATTEMPTS})...")
        
        def delayed_reconnect():
            self._pending_reconnect = False
            if not self._should_reconnect:
                return
            try:
                self.start_live_feed(self._symbols_to_subscribe, self._on_tick_callback)
                logger.info(f"✅ Reconnected successfully after {self._reconnect_attempts} attempts")
            except Exception as e:
                logger.error(f"❌ Reconnection failed: {e}")
                self._schedule_reconnect()
        
        self._reconnect_thread = threading.Timer(delay, delayed_reconnect)
        self._reconnect_thread.daemon = True
        self._reconnect_thread.start()

    def close(self):
        self._should_reconnect = False
        if self._reconnect_thread:
            self._reconnect_thread.cancel()
        if self.socket_opened:
            self.api.close_websocket()
            print("🔌 Connection closed")
