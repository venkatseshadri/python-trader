#!/usr/bin/env python3
"""
ORBITER BrokerClient - Production Shoonya API Wrapper
VENKAT SESHADRI | FA333160 | LIVE Feb 2026
FIXED: All imports + symbol mapping ✅
"""

import sys
import os
import json
import requests
import zipfile
import io
import pandas as pd
import datetime
import calendar

# Add ShoonyaApi-py to path for api_helper import
shoonya_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'ShoonyaApi-py')
sys.path.insert(0, shoonya_path)

from api_helper import ShoonyaApiPy
import yaml
import logging
from typing import Dict, Optional, Any
from NorenRestApiPy.NorenApi import position
from config.config import VERBOSE_LOGS

class BrokerClient:
    def __init__(self, config_path: str = '../cred.yml', segment_name: str = 'nfo'):
        self.api = ShoonyaApiPy()
        self.socket_opened = False
        self.segment_name = segment_name.lower()
        self.SYMBOLDICT: Dict[str, Dict[str, Any]] = {}
        self.TOKEN_TO_SYMBOL: Dict[str, str] = {}
        self.SYMBOL_TO_TOKEN: Dict[str, str] = {}
        self.TOKEN_TO_COMPANY: Dict[str, str] = {}  # ✅ Add company name mapping
        self.NFO_OPTIONS = []
        self.NFO_OPTIONS_LOADED = False
        self.span_cache_path = None
        self.span_cache = None
        
        # Load credentials
        orbiter_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_file = os.path.abspath(os.path.join(orbiter_root, config_path))
        with open(self.config_file) as f:
            self.cred = yaml.load(f, Loader=yaml.FullLoader)
            
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("websocket").setLevel(logging.WARNING)
        print(f"🚀 BrokerClient initialized: {self.cred['user']} for {self.segment_name.upper()}")
        self.verbose_logs = VERBOSE_LOGS

        self.trade_log_path = os.path.join(orbiter_root, 'logs', 'trade_calls.log')
        os.makedirs(os.path.dirname(self.trade_log_path), exist_ok=True)
        self.trade_logger = logging.getLogger("trade_calls")
        self.trade_logger.setLevel(logging.INFO)
        if not any(isinstance(h, logging.FileHandler) and h.baseFilename == self.trade_log_path for h in self.trade_logger.handlers):
            handler = logging.FileHandler(self.trade_log_path)
            handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
            self.trade_logger.addHandler(handler)
        
        # 🔥 CRITICAL: Load FULL symbol mapping
        self.load_symbol_mapping()

    def set_span_cache_path(self, path: str):
        self.span_cache_path = path

    def load_span_cache(self):
        if not self.span_cache_path:
            return
        if self.span_cache is not None:
            return
        try:
            if os.path.exists(self.span_cache_path):
                with open(self.span_cache_path, 'r') as f:
                    self.span_cache = json.load(f)
            else:
                self.span_cache = {}
        except Exception:
            self.span_cache = {}

    def save_span_cache(self):
        if not self.span_cache_path or self.span_cache is None:
            return
        try:
            os.makedirs(os.path.dirname(self.span_cache_path), exist_ok=True)
            with open(self.span_cache_path, 'w') as f:
                json.dump(self.span_cache, f)
        except Exception:
            pass

    def _parse_expiry_date(self, raw: str) -> Optional[datetime.date]:
        if not raw:
            return None
        for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
        return None

    def _is_last_thursday(self, d: datetime.date) -> bool:
        last_day = calendar.monthrange(d.year, d.month)[1]
        last_date = datetime.date(d.year, d.month, last_day)
        while last_date.weekday() != 3:
            last_date -= datetime.timedelta(days=1)
        return d == last_date

    def load_futures_map(self):
        """Load Futures from specialized mapping file for the active segment"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Determine specific file for segment
        map_filename = f"{self.segment_name}_futures_map.json"
        map_file = os.path.join(base_dir, 'data', map_filename)
        
        if os.path.exists(map_file):
            try:
                with open(map_file, 'r') as f:
                    fut_data = json.load(f)
                    count = 0
                    for tok_id, info in fut_data.items():
                        t_str = str(tok_id).strip()
                        # Store both raw and prefixed for robustness
                        prefixed = f"{self.segment_name.upper()}|{t_str}"
                        
                        if isinstance(info, list) and len(info) >= 2:
                            tsym = info[1]
                            base = info[0]
                        else:
                            tsym = f"{info} FUT"
                            base = info
                        
                        self.TOKEN_TO_SYMBOL[t_str] = tsym
                        self.TOKEN_TO_SYMBOL[prefixed] = tsym
                        self.TOKEN_TO_COMPANY[t_str] = base
                        count += 1
                print(f"✅ Loaded {count} {self.segment_name.upper()} futures from {map_filename}")
            except Exception as e:
                print(f"⚠️ Failed to load {map_file}: {e}")
        else:
            print(f"⚠️ No futures map found for {self.segment_name.upper()} at {map_file}")

    def load_symbol_mapping(self):
        """Load NSE base map and then layer segment-specific futures on top"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_file = os.path.join(base_dir, 'data', 'nse_token_map.json')
        
        needs_download = False
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    self.TOKEN_TO_SYMBOL = data.get('token_to_symbol', {})
                    self.SYMBOL_TO_TOKEN = data.get('symbol_to_token', {})
                    self.TOKEN_TO_COMPANY = data.get('token_to_company', {})
                    print(f"✅ Loaded {len(self.TOKEN_TO_SYMBOL):,} NSE symbols")
            except Exception: needs_download = True
        else: needs_download = True
        
        if needs_download:
            print("📥 INITIALIZING FRESH SCRIP MASTERS...")
            self.download_scrip_master("NSE")
            self.download_scrip_master("NFO")
            self.download_scrip_master("MCX")
        
        # Always layer segment-specific futures
        self.load_futures_map()

    def _get_option_rows(self, symbol: str, expiry: datetime.date, instrument: str = "OPTSTK"):
        if not self.NFO_OPTIONS_LOADED:
            self.load_nfo_symbol_mapping()

        expiry_str = expiry.isoformat()
        exchange = 'MCX' if instrument in ('OPTCOM', 'FUTCOM', 'OPTFUT') else 'NFO'
        
        # Determine valid instruments for this search
        inst_group = (instrument,)
        if instrument == 'OPTSTK': inst_group = ('OPTSTK', 'FUTSTK')
        elif instrument == 'OPTIDX': inst_group = ('OPTIDX', 'FUTIDX')
        elif instrument in ('OPTCOM', 'OPTFUT'): 
            inst_group = ('OPTCOM', 'OPTFUT') # Only options

        search_symbol = symbol.upper().strip()

        return [
            row for row in self.NFO_OPTIONS
            if (row.get('symbol', '').upper().strip() == search_symbol or (exchange == 'MCX' and search_symbol in row.get('symbol', '').upper()))
            and row.get('instrument') in inst_group 
            and row.get('expiry') == expiry_str and row.get('exchange') == exchange
        ]

    def _select_expiry(self, symbol: str, expiry_type: str = "monthly", instrument: str = "OPTSTK") -> Optional[datetime.date]:
        if not self.NFO_OPTIONS_LOADED:
            self.load_nfo_symbol_mapping()

        expiries = set()
        exchange = 'MCX' if instrument in ('OPTCOM', 'FUTCOM', 'OPTFUT') else 'NFO'
        
        # Match instrument groups
        inst_group = (instrument,)
        if instrument == 'OPTSTK': inst_group = ('OPTSTK', 'FUTSTK')
        elif instrument == 'OPTIDX': inst_group = ('OPTIDX', 'FUTIDX')
        elif instrument in ('OPTCOM', 'OPTFUT'): 
            inst_group = ('OPTCOM', 'OPTFUT') # Only options

        search_symbol = symbol.upper().strip()

        for row in self.NFO_OPTIONS:
            row_sym = row.get('symbol', '').upper().strip()
            if not (row_sym == search_symbol or (exchange == 'MCX' and search_symbol in row_sym)):
                continue
            if row.get('instrument') not in inst_group or row.get('exchange') != exchange:
                continue
            exp = self._parse_expiry_date(row.get('expiry'))
            if exp:
                expiries.add(exp)

        if not expiries:
            return None

        today = datetime.date.today()
        valid = sorted(d for d in expiries if d >= today)
        if not valid:
            return None

        if expiry_type == "monthly":
            monthly = [d for d in valid if self._is_last_thursday(d)]
            if monthly:
                return monthly[0]
            
            if exchange == 'MCX':
                return valid[0]
            
            return valid[0]

        return valid[0]

    def get_near_future(self, symbol: str, exchange: str = 'NFO') -> Optional[Dict[str, str]]:
        """Get the token and tsym for the nearest expiry Future contract."""
        try:
            ret = self.api.searchscrip(exchange=exchange, searchtext=symbol)
            if ret and ret.get('stat') == 'Ok' and 'values' in ret:
                candidates = []
                today = datetime.date.today()
                for scrip in ret['values']:
                    valid_inst = ('FUTSTK', 'FUTIDX', 'FUTCOM')
                    if scrip.get('instname') in valid_inst and scrip.get('symname') == symbol:
                        exp_str = scrip.get('exp') or scrip.get('exd')
                        exp = self._parse_expiry_date(exp_str)
                        if exp and exp >= today:
                            candidates.append((exp, scrip['token'], scrip.get('tsym')))
                
                if candidates:
                    candidates.sort(key=lambda x: x[0])
                    return {
                        'token': f"{exchange}|{candidates[0][1]}",
                        'tsym': candidates[0][2]
                    }
        except Exception:
            pass
        return None

    def place_future_order(self, symbol: str, token: str, side: str, execute: bool = False,
                           product_type: str = "I", price_type: str = "MKT") -> Dict[Any, Any]:
        """Place a direct Future order (Long or Short)"""
        # WS uses full key: 'MCX|467013'
        data = self.SYMBOLDICT.get(token)
        tsym = data.get('tsym') if data else None
        
        # Standardize Token ID for mapping lookups
        t_id_only = str(token.split('|')[-1]).strip()
        exch = token.split('|')[0] if '|' in token else 'MCX'

        # Fallback to TOKEN_TO_SYMBOL mapping
        if not tsym:
            tsym = self.TOKEN_TO_SYMBOL.get(t_id_only)

        if not tsym:
            return {'ok': False, 'reason': f'future_not_found'}

        # Determine lot size
        lot_size = int(data.get('ls', 1)) if data and data.get('ls') else 1
        if lot_size == 1:
            row = next((r for r in self.NFO_OPTIONS if r['token'] == t_id_only), None)
            if row: lot_size = int(row.get('lot_size', 1))

        if not execute:
            self.trade_logger.info("sim_order side=%s exch=%s symbol=%s qty=%s", side, exch, tsym, lot_size)
            return {'ok': True, 'tsym': tsym, 'lot_size': lot_size, 'dry_run': True}

        resp = self.api.place_order(buy_or_sell=side, product_type=product_type, exchange=exch,
                                   tradingsymbol=tsym, quantity=lot_size, discloseqty=0,
                                   price_type=price_type, price=0, trigger_price=None,
                                   retention='DAY', remarks='orb_future')
        
        if not resp or resp.get('stat') != 'Ok':
            return {'ok': False, 'reason': 'future_order_failed', 'resp': resp}

        return {'ok': True, 'tsym': tsym, 'lot_size': lot_size, 'resp': resp}
    
    def login(self, factor2_override: Optional[str] = None) -> bool:
        print("🔐 Authenticating...")
        two_fa = ""
        if factor2_override:
            two_fa = factor2_override.strip()
        elif self.cred.get('totp_key'):
            try:
                import pyotp
                totp = pyotp.TOTP(self.cred['totp_key'].replace(" ", ""))
                two_fa = totp.now()
                print(f"🤖 Automated TOTP generated")
            except Exception as e:
                print(f"⚠️ TOTP generation failed: {e}")

        if not two_fa:
            try:
                current = self.cred.get('factor2', '')
                two_fa = input(f"Enter 2FA (current: {current}): ").strip() or current
            except:
                two_fa = self.cred.get('factor2', '')

        ret = self.api.login(userid=self.cred['user'], password=self.cred['pwd'], twoFA=two_fa,
                           vendor_code=self.cred['vc'], api_secret=self.cred['apikey'], imei=self.cred['imei'])
        
        if not ret or str(ret.get('stat', '')).lower() != 'ok':
            return False
        
        self.load_symbol_mapping()
        return True
    
    def start_live_feed(self, symbols: list):
        print(f"🚀 Starting WS for {len(symbols)} symbols...")
        self.symbols = symbols
        token_to_exch = {s.split('|')[1]: s.split('|')[0] for s in symbols if '|' in s}

        def on_tick(message):
            if 'lp' not in message: return
            token = str(message.get('tk', ''))
            exch = token_to_exch.get(token, 'NSE')
            key = f"{exch}|{token}"
            
            symbol = self.get_symbol(token, exchange=exch)
            self.SYMBOLDICT[key] = {
                **message, 'symbol': symbol, 'token': token, 'exchange': exch,
                'tsym': message.get('tsym', symbol), 'ls': message.get('ls', 1),
                'ltp': float(message['lp']), 'high': float(message.get('h', 0)),
                'low': float(message.get('l', 0)), 'volume': int(message.get('v', 0))
            }
        
        self.api.start_websocket(subscribe_callback=on_tick, 
                               socket_open_callback=lambda: self.api.subscribe(self.symbols, feed_type='d'))
    
    def get_ltp(self, exch_token: str) -> Optional[float]:
        return self.SYMBOLDICT.get(exch_token, {}).get('ltp')

    def load_nfo_symbol_mapping(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_file = os.path.join(base_dir, 'data', 'nfo_symbol_map.json')
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                self.NFO_OPTIONS = json.load(f).get('options', [])
                self.NFO_OPTIONS_LOADED = True

    def download_scrip_master(self, exchange: str):
        url = f"https://api.shoonya.com/{exchange}_symbols.txt.zip"
        print(f"📥 Downloading {exchange} symbols...")
        try:
            r = requests.get(url, timeout=15)
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open(f"{exchange}_symbols.txt") as f:
                    lines = f.readlines()
                    headers = lines[0].decode().strip().split(',')
                    token_idx = headers.index("Token")
                    symbol_idx = headers.index("Symbol")
                    tsym_idx = headers.index("TradingSymbol")
                    inst_idx = headers.index("Instrument")
                    
                    if exchange == "NSE":
                        self.TOKEN_TO_SYMBOL, self.SYMBOL_TO_TOKEN, token_to_company = {}, {}, {}
                        for line in lines[1:]:
                            parts = line.decode().strip().split(',')
                            if len(parts) > symbol_idx:
                                token = str(int(parts[token_idx].strip()))
                                symbol = parts[symbol_idx].strip().replace(' ', '')
                                self.TOKEN_TO_SYMBOL[token] = symbol
                                self.SYMBOL_TO_TOKEN[symbol] = token
                                token_to_company[token] = parts[symbol_idx].strip()
                        
                        cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'nse_token_map.json')
                        with open(cache_file, 'w') as f_out:
                            json.dump({'token_to_symbol': self.TOKEN_TO_SYMBOL, 'symbol_to_token': self.SYMBOL_TO_TOKEN, 'token_to_company': token_to_company}, f_out)
                    else:
                        exp_i = headers.index("Expiry")
                        strike_i = headers.index("StrikePrice")
                        opt_i = headers.index("OptionType")
                        lot_i = headers.index("LotSize")
                        new_options = []
                        valid_inst = ("OPTSTK", "OPTIDX", "FUTSTK", "FUTIDX", "FUTCOM", "OPTCOM", "OPTFUT")
                        for line in lines[1:]:
                            parts = line.decode().strip().split(',')
                            if len(parts) > inst_idx and parts[inst_idx].strip() in valid_inst:
                                exp = self._parse_expiry_date(parts[exp_i].strip())
                                if not exp: continue
                                new_options.append({
                                    'symbol': parts[symbol_idx].strip(), 'tradingsymbol': parts[tsym_idx].strip(),
                                    'instrument': parts[inst_idx].strip(), 'exchange': exchange,
                                    'expiry': exp.isoformat(), 'strike': float(parts[strike_i].strip() or 0),
                                    'option_type': parts[opt_i].strip(), 'lot_size': int(float(parts[lot_i].strip() or 0)),
                                    'token': parts[token_idx].strip()
                                })
                        
                        cache_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'nfo_symbol_map.json')
                        existing = []
                        if os.path.exists(cache_file):
                            try: existing = json.load(open(cache_file)).get('options', [])
                            except: pass
                        self.NFO_OPTIONS = [r for r in existing if r.get('exchange') != exchange] + new_options
                        with open(cache_file, 'w') as f_out: json.dump({'options': self.NFO_OPTIONS}, f_out)
        except Exception as e: print(f"⚠️ {exchange} download failed: {e}")

    def get_dk_levels(self, exch_token: str) -> Dict[str, float]:
        d = self.SYMBOLDICT.get(exch_token, {})
        return {'ltp': d.get('ltp', 0), 'high': d.get('high', 0), 'low': d.get('low', 0)}
