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

# Add ShoonyaApi-py to path for api_helper import
shoonya_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'ShoonyaApi-py')
sys.path.insert(0, shoonya_path)

from api_helper import ShoonyaApiPy
import yaml
import logging
from typing import Dict, Optional, Any

class BrokerClient:
    def __init__(self, config_path: str = '../cred.yml'):
        self.api = ShoonyaApiPy()
        self.socket_opened = False
        self.SYMBOLDICT: Dict[str, Dict[str, Any]] = {}
        self.TOKEN_TO_SYMBOL: Dict[str, str] = {}
        self.SYMBOL_TO_TOKEN: Dict[str, str] = {}
        self.TOKEN_TO_COMPANY: Dict[str, str] = {}  # ✅ Add company name mapping
        
        # Load credentials
        # client.py is at: python-trader/orbiter/core/client.py
        # We need to find python-trader root (3 levels up)
        orbiter_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_file = os.path.abspath(os.path.join(orbiter_root, config_path))
        with open(self.config_file) as f:
            self.cred = yaml.load(f, Loader=yaml.FullLoader)
            
        logging.basicConfig(level=logging.DEBUG)
        print(f"🚀 BrokerClient initialized: {self.cred['user']}")
        
        # 🔥 CRITICAL: Load FULL symbol mapping
        self.load_symbol_mapping()
    
    def login(self) -> bool:
        print("🔐 Authenticating...")
        # Prompt for fresh 2FA every run and persist it to cred.yml
        try:
            current = self.cred.get('factor2', '')
            new2 = input(f"Enter 2FA (current: {current}) or press Enter to keep: ").strip()
            if new2:
                self.cred['factor2'] = new2
                try:
                    with open(self.config_file, 'w') as f:
                        yaml.dump(self.cred, f)
                    print(f"🔒 Updated 2FA in {self.config_file}")
                except Exception as e:
                    print(f"⚠️ Failed to save credentials: {e}")
        except Exception:
            # non-interactive environment: proceed with existing value
            pass
        ret = self.api.login(
            userid=self.cred['user'],
            password=self.cred['pwd'],
            twoFA=self.cred['factor2'],
            vendor_code=self.cred['vc'],
            api_secret=self.cred['apikey'],
            imei=self.cred['imei']
        )
        # 🔥 CRITICAL: Ensure symbol mapping is loaded before WebSocket data
        if not self.TOKEN_TO_SYMBOL:
            print("📥 Symbol mapping not loaded, loading now...")
            self.load_symbol_mapping()
        return bool(ret)
    
    def start_live_feed(self, symbols: list):
        """🚀 PRODUCTION WEBSOCKET - FULLY WORKING"""
        print(f"🚀 Starting WS for {len(symbols)} symbols...")
        self.symbols = symbols  # 🔥 FIXED: Store symbols
        
        def on_tick(message):
            if 'lp' not in message: return
            token = str(message.get('tk', ''))
            exch = message.get('e', 'NSE')
            key = f"{exch}|{token}"
            
            symbol = self.get_symbol(token)
            self.SYMBOLDICT[key] = {
                **message,
                'symbol': symbol,
                't': symbol,  # ✅ Add 't' field for company name (used by safe_ltp)
                'company_name': self.get_company_name(token),  # ✅ Full company name
                'token': token,
                'exchange': exch,
                'ltp': float(message['lp']),
                'high': float(message.get('h', 0)),
                'low': float(message.get('l', 0)),
                'volume': int(message.get('v', 0))
            }
            
            symbol = self.get_symbol(token)
            print(f"📊 LIVE: {symbol} ({token}): ₹{message['lp']}")
        
        def on_open():
            self.socket_opened = True
            print("🚀 WEBSOCKET LIVE!")
            self.api.subscribe(self.symbols, feed_type='d')  # ✅ symbols defined
        
        self.api.start_websocket(
            subscribe_callback=on_tick,
            socket_open_callback=on_open,
            order_update_callback=lambda x: print("📋 ORDER:", x)
        )
    
    def get_ltp(self, exch_token: str) -> Optional[float]:
        """🔥 FIXED: Use 'ltp' not 'lp'"""
        data = self.SYMBOLDICT.get(exch_token, {})
        return data.get('ltp') if data else None
    
    def get_dk_levels(self, exch_token: str) -> Dict[str, float]:
        """🎯 Day's Key Levels for ORB"""
        data = self.SYMBOLDICT.get(exch_token, {})
        return {
            'ltp': data.get('ltp', 0),
            'high': data.get('high', 0),
            'low': data.get('low', 0)
        }
    
    def close(self):
        if self.socket_opened:
            self.api.close_websocket()
            print("🔌 Connection closed")

    # 🔥 SYMBOL MAPPING (unchanged - perfect)
    def load_symbol_mapping(self):
        # ✅ Use absolute path based on script location
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        json_file = os.path.join(base_dir, 'data', 'nse_token_map.json')
        
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    self.TOKEN_TO_SYMBOL = data['token_to_symbol']
                    self.SYMBOL_TO_TOKEN = data['symbol_to_token']
                    self.TOKEN_TO_COMPANY = data.get('token_to_company', {})  # ✅ Load company names
                    
                    # 🔍 ADD THIS DEBUG:
                    print("🔍 SAMPLE MAPPING:")
                    for token in ['1394', '1660', '3045']:
                        symbol = self.TOKEN_TO_SYMBOL.get(token, 'MISSING')
                        company = self.TOKEN_TO_COMPANY.get(token, symbol)
                        print(f"   NSE|{token} → {symbol} ({company})")
                    
                    print(f"✅ Loaded {len(self.TOKEN_TO_SYMBOL):,} symbols")
                    return
            except Exception as e:
                print(f"⚠️ Cache invalid: {e}")
        
        print("📥 DOWNLOADING FRESH SYMBOLS...")
        self.download_scrip_master()
    
    def download_scrip_master(self):
        """🔥 FIXED: Handle Shoonya NSE_symbols.txt CSV format (comma-separated, not pipes!)"""
        print("📥 Downloading NSE_symbols.txt.zip...")
        try:
            r = requests.get("https://api.shoonya.com/NSE_symbols.txt.zip", timeout=10)
            r.raise_for_status()
            
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open("NSE_symbols.txt") as f:
                    # 🔥 CSV FORMAT: Exchange,Token,LotSize,Symbol,TradingSymbol,Instrument,TickSize,...
                    lines = f.readlines()
                    headers = lines[0].decode().strip().rstrip(',').split(',')  # ✅ COMMA-separated!
                    
                    print(f"🔍 DEBUG: Found {len(headers)} columns")
                    
                    # CSV columns: [Exchange, Token, LotSize, Symbol, TradingSymbol, Instrument, TickSize, ...]
                    token_idx = 1  # Token is column 1
                    symbol_idx = 3  # Symbol (company name) is column 3
                    tsym_idx = 4    # TradingSymbol is column 4
                    
                    self.TOKEN_TO_SYMBOL = {}
                    self.SYMBOL_TO_TOKEN = {}
                    token_to_company = {}  # ✅ Track company names
                    
                    for i, line in enumerate(lines[1:]):  # Skip header
                        parts = line.decode().strip().rstrip(',').split(',')
                        if len(parts) > max(token_idx, symbol_idx, tsym_idx):
                            try:
                                token = str(int(parts[token_idx].strip()))
                                company_name = parts[symbol_idx].strip()  # e.g., "RELIANCE"
                                tsym = parts[tsym_idx].strip()  # e.g., "RELIANCE-EQ"
                                
                                # Extract clean symbol (remove -EQ suffixes)
                                symbol = company_name.replace(' ', '')  # Use company name as symbol
                                
                                self.TOKEN_TO_SYMBOL[token] = symbol
                                self.SYMBOL_TO_TOKEN[symbol] = token
                                
                                # For company name, use the full trading symbol or company
                                if company_name:
                                    token_to_company[token] = company_name
                                
                                # 🔍 DEBUG: Show first few extracted
                                if i < 5:
                                    print(f"🔍 Row {i}: token={token}, symbol={symbol}, company={company_name}")
                            except (ValueError, IndexError) as e:
                                continue  # Skip bad rows
                    
            # ✅ Use absolute path for saving
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, 'data')
            os.makedirs(data_dir, exist_ok=True)
            cache_file = os.path.join(data_dir, 'nse_token_map.json')
            
            cache_data = {
                'token_to_symbol': self.TOKEN_TO_SYMBOL,
                'symbol_to_token': self.SYMBOL_TO_TOKEN,
                'token_to_company': token_to_company
            }
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f)
            print(f"✅ Cached {len(self.TOKEN_TO_SYMBOL):,} symbols at {cache_file}")
            
        except Exception as e:
            print(f"⚠️ Download failed: {e}, using fallback mapping...")
            self.TOKEN_TO_SYMBOL = self.get_fallback_mapping()
  
    def get_fallback_mapping(self) -> Dict[str, str]:
        """✅ Comprehensive fallback with company names - from login watchlist data"""
        fallback = {
            '2885': 'RELIANCE',
            '11630': 'NTPC', 
            '3045': 'SBIN',
            '317': 'BAJFINANCE', 
            '1333': 'HDFCBANK', 
            '1660': 'ITC',
            '1394': 'HINDUNILVR',
            '9819': 'HAVELLS',
            '2475': 'ONGC',
            '14977': 'POWERGRID',
            '17881': 'DBCORP',
            '759084': 'URBANCO',
            '3703': 'VIPIND',
            '15355': 'RECLTD',
            '14299': 'PFC',
            '383': 'BEL',
            '526': 'EXIDEIND',
        }
        
        # ✅ Create TOKEN_TO_COMPANY mapping
        self.TOKEN_TO_COMPANY = {
            '2885': 'RELIANCE INDUSTRIES LTD',
            '11630': 'NTPC LTD',
            '3045': 'STATE BANK OF INDIA',
            '317': 'BAJAJ FINANCE LIMITED',
            '1333': 'HDFC BANK LTD',
            '1660': 'ITC LTD',
            '1394': 'HINDUSTAN UNILEVER LTD.',
            '9819': 'HAVELLS INDIA LIMITED',
            '2475': 'OIL AND NATURAL GAS CORP.',
            '14977': 'POWER GRID CORP. LTD.',
            '17881': 'D.B.CORP LTD',
            '759084': 'URBAN COMPANY LIMITED',
            '3703': 'VIP INDUSTRIES LTD',
            '15355': 'REC LIMITED',
            '14299': 'POWER FIN CORP LTD.',
            '383': 'BHARAT ELECTRONICS LTD',
            '526': 'EXIDE INDUSTRIES LIMITED',
        }
        
        self.SYMBOL_TO_TOKEN.update({v: k for k, v in fallback.items()})
        return fallback
    
    def get_symbol(self, token: str) -> str:
        return self.TOKEN_TO_SYMBOL.get(token, f"NSE|{token}")
    
    def get_company_name(self, token: str) -> str:
        """✅ Get company name for token, fallback to symbol"""
        return self.TOKEN_TO_COMPANY.get(token, self.get_symbol(token))
    
    def get_token(self, symbol: str) -> str:
        return self.SYMBOL_TO_TOKEN.get(symbol.upper(), symbol)
