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
        o_ok = False
        if segment_name.lower() == 'nfo':
            o_ok = self.options.load_cache()

        if not f_ok or (segment_name.lower() == 'nfo' and not o_ok):
            self.download_scrip_master("NFO")
            if segment_name.lower() == 'mcx':
                self.download_scrip_master("MCX")

        # 3. Load local futures mapping (Primary source for lot sizes)
        self.load_segment_futures_map(segment_name)

    def load_segment_futures_map(self, segment_name='nfo'):
        """Load mapping files created by utilities"""
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
        """Unified downloader proxy"""
        if exchange == "NSE":
            self._download_nse()
        else:
            self._download_derivative_exchange(exchange)

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
