import os
import logging
import json
from typing import Dict, Optional, Any, List
from .connection import ConnectionManager
from .master import ScripMaster
from .resolver import ContractResolver
from .margin import MarginCalculator
from .executor import OrderExecutor

class BrokerClient:
    def __init__(self, config_path: str = '../cred.yml', segment_name: str = 'nfo'):
        self.segment_name = segment_name.lower()
        self.conn = ConnectionManager(config_path)
        self.master = ScripMaster()
        self.resolver = ContractResolver(self.master)
        self.margin = MarginCalculator(self.master)
        self.executor = OrderExecutor(self.conn.api, self._init_logger())
        
        self.SYMBOLDICT: Dict[str, Dict[str, Any]] = {}
        self.span_cache_path = None
        self._span_cache = None
        
        # Load only relevant mappings for this segment
        self.load_symbol_mapping()

    def _init_logger(self):
        orbiter_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        log_dir = os.path.join(orbiter_root, 'logs', self.segment_name)
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, 'trade_calls.log')
        
        logger = logging.getLogger(f"trade_calls_{self.segment_name}")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            h = logging.FileHandler(path)
            h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
            logger.addHandler(h)
        return logger

    @property
    def api(self): return self.conn.api
    @property
    def TOKEN_TO_SYMBOL(self): return self.master.TOKEN_TO_SYMBOL
    @property
    def SYMBOL_TO_TOKEN(self): return self.master.SYMBOL_TO_TOKEN
    @property
    def TOKEN_TO_COMPANY(self): return self.master.TOKEN_TO_COMPANY
    @property
    def DERIVATIVE_OPTIONS(self): return self.master.DERIVATIVE_OPTIONS
    @property
    def DERIVATIVE_LOADED(self): return self.master.DERIVATIVE_LOADED
    
    @property
    def span_cache(self): 
        return self._span_cache if self._span_cache is not None else {}

    def login(self, factor2_override=None): 
        return self.conn.login(factor2_override)

    def start_live_feed(self, symbols):
        def _tick_handler(msg, tk, ex):
            key = f"{ex}|{tk}"
            sym = self.get_symbol(tk, exchange=ex)
            self.SYMBOLDICT[key] = {
                **msg, 'symbol': sym, 't': sym, 'company_name': self.get_company_name(tk, exchange=ex),
                'token': tk, 'exchange': ex, 'ltp': float(msg['lp']),
                'high': float(msg.get('h', 0)), 'low': float(msg.get('l', 0)), 'volume': int(msg.get('v', 0))
            }
        self.conn.start_live_feed(symbols, _tick_handler)

    def close(self): self.conn.close()
    def load_symbol_mapping(self): self.master.load_mappings(self.segment_name)
    def download_scrip_master(self, exchange): self.master.download_scrip_master(exchange)
    def load_nfo_futures_map(self): self.master.load_segment_futures_map(self.segment_name)
    
    def set_span_cache_path(self, path): 
        self.span_cache_path = path

    def load_span_cache(self):
        if not self.span_cache_path: return
        try:
            if os.path.exists(self.span_cache_path):
                with open(self.span_cache_path, 'r') as f:
                    self._span_cache = json.load(f)
            else: self._span_cache = {}
        except Exception: self._span_cache = {}

    def save_span_cache(self):
        if not self.span_cache_path or self._span_cache is None: return
        try:
            os.makedirs(os.path.dirname(self.span_cache_path), exist_ok=True)
            with open(self.span_cache_path, 'w') as f:
                json.dump(self._span_cache, f)
        except Exception: pass

    def get_symbol(self, token, exchange='NSE'): return self.master.TOKEN_TO_SYMBOL.get(token, f"{exchange}|{token}")
    def get_company_name(self, token, exchange='NSE'): return self.master.TOKEN_TO_COMPANY.get(token, self.get_symbol(token, exchange))
    def get_token(self, symbol): return self.master.SYMBOL_TO_TOKEN.get(symbol.upper(), symbol)
    def get_ltp(self, key): return self.SYMBOLDICT.get(key, {}).get('ltp')
    def get_dk_levels(self, key): 
        d = self.SYMBOLDICT.get(key, {})
        return {'ltp': d.get('ltp', 0), 'high': d.get('high', 0), 'low': d.get('low', 0)}

    def get_near_future(self, symbol, exchange='NFO'): return self.resolver.get_near_future(symbol, exchange, self.api)
    def get_credit_spread_contracts(self, symbol, ltp, side, hedge_steps=4, expiry_type="monthly", instrument="OPTSTK"):
        return self.resolver.get_credit_spread_contracts(symbol, ltp, side, hedge_steps, expiry_type, instrument)
    def calculate_span_for_spread(self, spread, product_type="I", haircut=0.20):
        return self.margin.calculate_span_for_spread(spread, self.api, self.conn.cred['user'], product_type, haircut)
    
    def calculate_future_margin(self, future_details, product_type="I", haircut=0.20):
        return self.margin.calculate_future_margin(future_details, self.api, self.conn.cred['user'], product_type, haircut)
    
    def get_option_ltp_by_symbol(self, tsym):
        # Optimized lookup for MCX
        if self.segment_name == 'mcx':
            # Futures only
            for k, v in self.SYMBOLDICT.items():
                if v.get('symbol') == tsym: return v.get('ltp')
        
        for r in self.master.DERIVATIVE_OPTIONS:
            if r.get('tradingsymbol') == tsym:
                q = self.api.get_quotes(exchange=r['exchange'], token=r['token'])
                return float(q.get('lp') or q.get('ltp') or 0) if q else None
        return None

    def place_put_credit_spread(self, **kwargs):
        res = self.resolver.get_credit_spread_contracts(kwargs['symbol'], kwargs['ltp'], 'PUT', kwargs['hedge_steps'], kwargs['expiry_type'], kwargs['instrument'])
        if not res.get('ok'): return res
        return self.executor.place_spread(res, kwargs['execute'], kwargs['product_type'], kwargs['price_type'])

    def place_call_credit_spread(self, **kwargs):
        res = self.resolver.get_credit_spread_contracts(kwargs['symbol'], kwargs['ltp'], 'CALL', kwargs['hedge_steps'], kwargs['expiry_type'], kwargs['instrument'])
        if not res.get('ok'): return res
        return self.executor.place_spread(res, kwargs['execute'], kwargs['product_type'], kwargs['price_type'])

    def place_future_order(self, **kwargs):
        """Place a single-leg Future trade (Long/Short)"""
        symbol, exchange = kwargs['symbol'], kwargs.get('exchange', 'NFO')
        res = self.resolver.get_near_future(symbol, exchange, self.api)
        
        # 🔥 Fallback: Check mapped futures directly if resolver/API failed
        if not res and kwargs.get('token'):
            token_in = str(kwargs.get('token'))
            tsym = self.master.TOKEN_TO_SYMBOL.get(token_in)
            if tsym:
                res = {'token': token_in, 'tsym': tsym}
                print(f"✅ Resolved via Map: {token_in} -> {tsym}")

        if not res: return {'ok': False, 'reason': 'future_not_found'}
        
        # print(f"🔍 Resolving lot size for {res['tsym']}...")
        lot_size = 0
        
        # 1️⃣ Priority: mcx_futures_map.json (Updated by utility)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        map_file = os.path.join(base_dir, 'data', f"{self.segment_name}_futures_map.json")
        if os.path.exists(map_file):
            try:
                with open(map_file, 'r') as f:
                    fut_data = json.load(f)
                    tok_id = res['token'].split("|")[-1]
                    info = fut_data.get(tok_id)
                    if info and len(info) >= 3:
                        lot_size = int(info[2])
                        print(f"✅ Found lot size in mapping: {lot_size}")
            except Exception: pass

        # 2️⃣ Fallback: derivative master cache
        if lot_size <= 0:
            for r in self.master.DERIVATIVE_OPTIONS:
                if r.get('tradingsymbol') == res['tsym']:
                    lot_size = int(r.get('lot_size', 0))
                    break
        
        if lot_size <= 0: 
            return {'ok': False, 'reason': 'invalid_lot_size'}
        
        details = {'tsym': res['tsym'], 'lot_size': lot_size, 'exchange': exchange, 'token': res['token']}
        return self.executor.place_future_order(details, kwargs['side'], kwargs['execute'], kwargs['product_type'], kwargs['price_type'])
