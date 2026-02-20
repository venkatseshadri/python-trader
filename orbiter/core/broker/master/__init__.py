import os
import json
import requests
import zipfile
import io
from typing import Dict, Any, List
from .equity import EquityManager
from .futures import FuturesManager
from .options import OptionsManager

class ScripMaster:
    def __init__(self, verbose=False):
        self.equity = EquityManager()
        self.futures = FuturesManager()
        self.options = OptionsManager()
        self.verbose = verbose
        
        # Facade pointers for backward compatibility
        self.TOKEN_TO_SYMBOL = self.equity.TOKEN_TO_SYMBOL
        self.SYMBOL_TO_TOKEN = self.equity.SYMBOL_TO_TOKEN
        self.TOKEN_TO_COMPANY = self.equity.TOKEN_TO_COMPANY
        self.TOKEN_TO_LOTSIZE: Dict[str, int] = {}  # 🔥 New: Cache lot sizes in memory

    @property
    def DERIVATIVE_OPTIONS(self):
        """Combined view for backward compatibility"""
        return self.futures.DATA + self.options.DATA

    @property
    def DERIVATIVE_LOADED(self):
        return len(self.futures.DATA) > 0

    def _parse_expiry_date(self, raw: str):
        return self.futures.parse_expiry_date(raw)

    def load_mappings(self, segment_name='nfo'):
        """Main entry point for loading segment data"""
        
        # 1. Load NSE if NFO segment
        if segment_name.lower() == 'nfo':
            if not self.equity.load_nse_mapping():
                self.download_scrip_master("NSE")
            # Sync facade pointers
            self.TOKEN_TO_SYMBOL.update(self.equity.TOKEN_TO_SYMBOL)
            self.SYMBOL_TO_TOKEN.update(self.equity.SYMBOL_TO_TOKEN)
            self.TOKEN_TO_COMPANY.update(self.equity.TOKEN_TO_COMPANY)

        # 2. Load Derivative Caches (Mode-Aware)
        f_ok = self.futures.load_cache()
        o_ok = self.options.load_cache()

        # If caches are empty or failed, force download
        if not f_ok or not o_ok:
            # Check if we can avoid the download via disk cache from today
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            cache_file = os.path.join(base_dir, 'orbiter', 'data', 'futures_master.json')
            from datetime import date
            is_fresh = os.path.exists(cache_file) and date.fromtimestamp(os.path.getmtime(cache_file)) == date.today()
            
            if not is_fresh:
                print("📦 Derivative caches empty/stale. Downloading masters...")
                self.download_scrip_master("NFO")
                self.download_scrip_master("MCX")
            else:
                # Still load them into memory if caches were somehow reported empty
                self.futures.load_cache()
                self.options.load_cache()

        # 3. Load local futures mapping (Primary source for lot sizes)
        self.load_segment_futures_map(segment_name)

    def load_segment_futures_map(self, segment_name='nfo'):
        """
        Load mapping files created by utilities (e.g., mcx_futures_map.json).
        
        CRITICAL: Implements "Dual-Key" Storage.
        - Stores raw token ID: '477167' -> 'COPPER27FEB26'
        - Stores prefixed ID: 'MCX|477167' -> 'COPPER27FEB26'
        
        This ensures that lookups succeed regardless of whether the input token 
        comes from a clean source or a prefixed WebSocket message.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        map_file = os.path.join(base_dir, 'data', f"{segment_name.lower()}_futures_map.json")
        
        if os.path.exists(map_file):
            try:
                with open(map_file, 'r') as f:
                    data = json.load(f)
                    for tok, info in data.items():
                        tok_str = str(tok).strip()
                        prefixed = f"{segment_name.upper()}|{tok_str}"
                        
                        if isinstance(info, list) and len(info) >= 2:
                            tsym, comp = info[1], info[0]
                            # Try to extract lot size if available (index 2)
                            if len(info) >= 3:
                                try:
                                    ls = int(info[2])
                                    self.TOKEN_TO_LOTSIZE[tok_str] = ls
                                    self.TOKEN_TO_LOTSIZE[prefixed] = ls
                                except: pass
                        else: 
                            tsym, comp = f"{info} FUT", info
                        
                        self.TOKEN_TO_SYMBOL[tok_str] = tsym
                        self.TOKEN_TO_SYMBOL[prefixed] = tsym
                        self.TOKEN_TO_COMPANY[tok_str] = comp
                print(f"✅ Loaded {len(data)} {segment_name.upper()} futures from mapping")
                return True
            except Exception: pass
        return False

    def download_scrip_master(self, exchange: str):
        """Unified downloader proxy with cache check"""
        # 🔥 CRITICAL: Prevent network calls in Test Mode
        if os.environ.get('ORBITER_TEST_MODE') == '1':
            if self.verbose: print(f"🧪 Test Mode: Skipping download for {exchange}")
            # Try loading from disk if available, but never hit network
            if exchange == "NSE": self.equity.load_nse_mapping()
            else: 
                self.futures.load_cache()
                self.options.load_cache()
            return True

        # 🔥 Optimization: Skip if already loaded in memory
        if exchange == "NFO" and len(self.futures.DATA) > 0: return
        if exchange == "MCX" and any(r.get('exchange') == 'MCX' for r in self.futures.DATA): return
        if exchange == "NSE" and len(self.equity.TOKEN_TO_SYMBOL) > 0: return

        # 🔥 Optimization: Skip if local cache file is from today
        from datetime import date
        import time
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        # Map exchange to internal cache file
        cache_file = None
        if exchange == "NSE": cache_file = os.path.join(base_dir, 'orbiter', 'data', 'nse_token_map.json')
        elif exchange == "NFO": cache_file = os.path.join(base_dir, 'orbiter', 'data', 'futures_master.json')
        elif exchange == "MCX": cache_file = os.path.join(base_dir, 'orbiter', 'data', 'futures_master.json')

        if cache_file and os.path.exists(cache_file):
            mtime = date.fromtimestamp(os.path.getmtime(cache_file))
            if mtime == date.today():
                if self.verbose: print(f"♻️  Using local {exchange} cache from today.")
                # Ensure data is loaded from cache if it exists
                if exchange == "NSE": self.equity.load_nse_mapping()
                else: 
                    self.futures.load_cache()
                    self.options.load_cache()
                return True

        if exchange == "NSE":
            return self._download_nse()
        else:
            return self._download_derivative_exchange(exchange)

    def _download_nse(self):
        url = "https://api.shoonya.com/NSE_symbols.txt.zip"
        print("📥 Downloading NSE master...")
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open("NSE_symbols.txt") as f:
                    lines = f.readlines()
                    headers = lines[0].decode().strip().rstrip(',').split(',')
                    t_i = headers.index("Token")
                    s_i = headers.index("Symbol")
                    
                    data_out = {'token_to_symbol': {}, 'symbol_to_token': {}, 'token_to_company': {}}
                    for line in lines[1:]:
                        parts = line.decode().strip().rstrip(',').split(',')
                        if len(parts) > max(t_i, s_i):
                            try:
                                token = str(int(parts[t_i].strip()))
                                symbol = parts[s_i].strip().replace(' ', '')
                                company = parts[s_i].strip()
                                data_out['token_to_symbol'][token] = symbol
                                data_out['symbol_to_token'][symbol] = token
                                data_out['token_to_company'][token] = company
                            except (ValueError, IndexError): continue
                    self.equity.save_nse_mapping(data_out)
                    self.equity.load_nse_mapping()
        except Exception as e: print(f"❌ NSE download failed: {e}")

    def _download_derivative_exchange(self, exchange: str):
        url = f"https://api.shoonya.com/{exchange}_symbols.txt.zip"
        filename = f"{exchange}_symbols.txt"
        print(f"📥 Downloading {exchange} Derivative master...")
        
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                with z.open(filename) as f:
                    lines = f.readlines()
                    headers = lines[0].decode().strip().rstrip(',').split(',')
                    
                    # Helper for column indices
                    def get_idx(name): return headers.index(name) if name in headers else None
                    
                    s_i, ts_i, inst_i, t_i = get_idx("Symbol"), get_idx("TradingSymbol"), get_idx("Instrument"), get_idx("Token")
                    exp_i, str_i, opt_i, lot_i = get_idx("Expiry"), get_idx("StrikePrice"), get_idx("OptionType"), get_idx("LotSize")

                    futures_rows, options_rows = [], []
                    for line in lines[1:]:
                        parts = line.decode().strip().rstrip(',').split(',')
                        if len(parts) <= max(filter(lambda x: x is not None, [s_i, ts_i, inst_i])): continue
                        
                        inst = parts[inst_i].strip()
                        expiry = self.futures.parse_expiry_date(parts[exp_i].strip() if exp_i is not None else '')
                        if not expiry: continue

                        row = {
                            'symbol': parts[s_i].strip(),
                            'tradingsymbol': parts[ts_i].strip(),
                            'instrument': inst,
                            'exchange': exchange,
                            'expiry': expiry.isoformat(),
                            'strike': float(parts[str_i].strip()) if str_i is not None and parts[str_i].strip() else 0.0,
                            'option_type': parts[opt_i].strip() if opt_i is not None else '',
                            'lot_size': int(float(parts[lot_i].strip())) if lot_i is not None and parts[lot_i].strip() else 0,
                            'token': parts[t_i].strip()
                        }

                        if inst.startswith('FUT'): futures_rows.append(row)
                        elif inst.startswith('OPT'): options_rows.append(row)

                    # Update Managers
                    self.futures.add_entries(futures_rows)
                    self.options.add_entries(options_rows)
                    
                    print(f"✅ Segmented {exchange}: {len(futures_rows)} Futures, {len(options_rows)} Options saved")
                    return True
        except Exception as e:
            print(f"❌ {exchange} download failed: {e}")
            return False
