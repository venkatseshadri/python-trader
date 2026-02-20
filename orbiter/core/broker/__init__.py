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
    """
    🚀 Central Gateway for Shoonya API Interactions.
    
    ARCHITECTURE:
    - Acts as a Facade over `ConnectionManager`, `ScripMaster`, and `OrderExecutor`.
    - Segment-Aware: Initialized with specific `segment_name` ('nfo', 'mcx').
    - State: Maintains `SYMBOLDICT` (Live WebSocket Feed).
    
    CRITICAL LOGIC:
    1. Token Resolution: Uses `ScripMaster` which implements a "Dual-Key" storage 
       (storing both raw '477167' and prefixed 'MCX|477167') to handle inconsistent inputs.
    2. Future Order Placement (`place_future_order`):
       - Priority 0: Check Live WS (`SYMBOLDICT`) for Lot Size (Most Accurate).
       - Priority 1: Check Memory Cache (`TOKEN_TO_LOTSIZE`) loaded from JSON maps.
       - Priority 2: Check Derivative Master (Fallback).
    """
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
        
        # 🔥 NEW: Force load master immediately to prevent mid-session stalls
        self.download_scrip_master('MCX' if self.segment_name == 'mcx' else 'NFO')
        
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
    def TOKEN_TO_LOTSIZE(self): return self.master.TOKEN_TO_LOTSIZE
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
            
            # 🔥 Preserve primed history if it exists
            existing_candles = self.SYMBOLDICT.get(key, {}).get('candles', [])
            
            self.SYMBOLDICT[key] = {
                **msg, 'symbol': sym, 't': sym, 'company_name': self.get_company_name(tk, exchange=ex),
                'token': tk, 'exchange': ex, 'ltp': float(msg['lp']),
                'high': float(msg.get('h', 0)), 'low': float(msg.get('l', 0)), 'volume': int(msg.get('v', 0)),
                'candles': existing_candles # Re-inject preserved candles
            }
        self.conn.start_live_feed(symbols, _tick_handler)

    def prime_candles(self, symbols: List[str], lookback_mins: int = 30):
        """Fetch historical 1-minute candles to satisfy entry guards immediately on startup"""
        if not symbols: return
        print(f"⏳ Priming {len(symbols)} symbols with last {lookback_mins}m data...")
        
        from datetime import datetime, timedelta
        import pytz
        
        ist = pytz.timezone('Asia/Kolkata')
        end_dt = datetime.now(ist)
        start_dt = end_dt - timedelta(minutes=lookback_mins + 15) # extra buffer for indicators
        
        success_count = 0
        for item in symbols:
            try:
                # Resolve key (EXCHANGE|TOKEN)
                if '|' in item: key = item
                else:
                    token = self.get_token(item)
                    exch = 'MCX' if self.segment_name == 'mcx' else 'NSE'
                    key = f"{exch}|{token}"
                
                ex, tk = key.split('|')
                res = self.api.get_time_price_series(exchange=ex, token=tk, starttime=int(start_dt.timestamp()), endtime=int(end_dt.timestamp()), interval=1)
                
                if res and isinstance(res, list):
                    if key not in self.SYMBOLDICT:
                        sym = self.get_symbol(tk, exchange=ex)
                        self.SYMBOLDICT[key] = {
                            'symbol': sym, 't': sym, 'company_name': self.get_company_name(tk, exchange=ex),
                            'token': tk, 'exchange': ex, 'ltp': float(res[-1]['intc']),
                            'high': float(res[-1].get('inth', 0)), 'low': float(res[-1].get('intl', 0)), 
                            'volume': int(res[-1].get('v', 0))
                        }
                    
                    self.SYMBOLDICT[key]['candles'] = res
                    success_count += 1
                else:
                    print(f"⚠️ No history returned for {key}")
            except Exception as e:
                print(f"⚠️ Failed to prime {item}: {e}")
        
        print(f"✅ Primed {success_count}/{len(symbols)} symbols successfully.")

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

    def get_limits(self):
        """Fetch granular margin and fund status from Shoonya."""
        try:
            res = self.api.get_limits()
            if not res or res.get('stat') != 'Ok':
                return None
            
            cash = float(res.get('cash', 0))
            collateral = float(res.get('collateral', 0))
            used = float(res.get('marginused', 0))
            
            # Total Buying Power = Cash + Collateral
            total_power = cash + collateral
            
            return {
                'liquid_cash': cash,              # Ledger Balance
                'collateral_value': collateral,   # Pledged Holdings (After Haircut)
                'margin_used': used,              # Blocked Margin
                'total_power': total_power,       # Total Margin (F in report)
                'available': total_power - used,  # Net Status (K in report)
                'payin': float(res.get('payin', 0))
            }
        except Exception as e:
            print(f"❌ Error fetching limits: {e}")
            return None

    def get_positions(self):
        """Fetch all open/overnight positions."""
        try:
            res = self.api.get_positions()
            if not res: return []
            return [p for p in res if p.get('stat') == 'Ok']
        except Exception as e:
            print(f"❌ Error fetching positions: {e}")
            return []

    def get_order_history(self):
        """Fetch orders to track session activity."""
        try:
            res = self.api.get_order_book()
            if not res: return []
            return [o for o in res if o.get('stat') == 'Ok']
        except Exception as e:
            print(f"❌ Error fetching order history: {e}")
            return []

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
        
        # 0️⃣ Priority: Live Data (SYMBOLDICT)
        if hasattr(self, 'SYMBOLDICT'):
            live_data = self.SYMBOLDICT.get(res['token'])
            if live_data and live_data.get('ls'):
                lot_size = int(live_data['ls'])
                # print(f"✅ Found lot size in Live Feed: {lot_size}")

                # 1️⃣ Priority: In-Memory Map Cache (Loaded at startup)

                if lot_size <= 0:

                    tok_id = str(res['token'].split("|")[-1])

                    cached_ls = self.TOKEN_TO_LOTSIZE.get(tok_id)

                    if cached_ls:

                        lot_size = cached_ls

                        # print(f"✅ Found lot size in Memory Cache: {lot_size}")

        

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
