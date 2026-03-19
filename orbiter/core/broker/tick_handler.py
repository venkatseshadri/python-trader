# orbiter/core/broker/tick_handler.py
"""
Tick Handler - manages websocket feed and tick data.
"""

import os
import json
import re
import logging
from typing import Dict, List, Any, Callable
from orbiter.core.broker.ltp_manager import LTPManager


class TickHandler:
    """Manages live tick feed from websocket."""
    
    def __init__(self, api, master, project_root: str, segment_name: str):
        self.api = api
        self.master = master
        self.project_root = project_root
        self.segment_name = segment_name
        self.logger = logging.getLogger("tick_handler")
        
        self.SYMBOLDICT: Dict[str, Dict[str, Any]] = {}
        self._tick_callbacks: List[Callable] = []
        
        self.ltp_manager = LTPManager(self)
    
    def register_tick_callback(self, callback: Callable):
        """Register a callback to be called on every tick."""
        self._tick_callbacks.append(callback)
        self.logger.debug(f"[TickHandler] Registered tick callback. Total: {len(self._tick_callbacks)}")
    
    def get_symbol(self, token, exchange='NSE'):
        """Get symbol for token."""
        return self.master.TOKEN_TO_SYMBOL.get(token, f"{exchange}|{token}")
    
    def get_company_name(self, token, exchange='NSE'):
        """Get company name for token."""
        return self.master.TOKEN_TO_COMPANY.get(token, self.get_symbol(token, exchange))
    
    def start_live_feed(self, connection, symbols):
        """Start live feed for given symbols."""
        self.logger.debug(f"[TickHandler] Starting live feed for {len(symbols)} symbols.")
        
        mcx_futures_map = self._load_futures_map('mcx')
        nfo_futures_map = self._load_futures_map('nfo')
        
        def resolve_to_token(token_or_symbol, exchange):
            if not isinstance(token_or_symbol, str):
                return str(token_or_symbol) if token_or_symbol else ""
            
            if isinstance(token_or_symbol, str) and token_or_symbol.isdigit():
                return token_or_symbol
            
            if mcx_futures_map and token_or_symbol.upper() in mcx_futures_map:
                mcx_entry = mcx_futures_map[token_or_symbol.upper()]
                numeric_token = str(mcx_entry[4]) if len(mcx_entry) > 4 else None
                if numeric_token:
                    return numeric_token
            
            if mcx_futures_map:
                for short_sym, mcx_entry in mcx_futures_map.items():
                    if isinstance(mcx_entry, list) and len(mcx_entry) > 1:
                        if isinstance(mcx_entry[1], str) and mcx_entry[1].upper() == token_or_symbol.upper():
                            return str(mcx_entry[4]) if len(mcx_entry) > 4 else None
            
            if nfo_futures_map:
                for num_token, entry in nfo_futures_map.items():
                    if isinstance(entry, list) and len(entry) >= 2:
                        if (isinstance(entry[0], str) and entry[0].upper() == token_or_symbol.upper()) or (isinstance(entry[1], str) and entry[1].upper() == token_or_symbol.upper()):
                            return num_token
            
            resolved = self.master.SYMBOL_TO_TOKEN.get(token_or_symbol.upper()) if isinstance(token_or_symbol, str) else None
            if resolved:
                return resolved
            
            for tok, tsym in self.master.TOKEN_TO_SYMBOL.items():
                if isinstance(tsym, str) and isinstance(token_or_symbol, str) and tsym.upper().startswith(token_or_symbol.upper()):
                    return tok
            
            return token_or_symbol
        
        resolved_symbols = []
        for s in symbols:
            if isinstance(s, dict):
                tk = str(s.get('token'))
                ex = s.get('exchange', 'NSE')
                resolved_tk = resolve_to_token(tk, ex)
                resolved_symbols.append({**s, 'token': resolved_tk})
            else:
                resolved_symbols.append(s)
        
        def _tick_handler(msg, tk, ex):
            key = f"{ex}|{tk}"
            sym = self.get_symbol(tk, exchange=ex)
            
            existing_data = self.SYMBOLDICT.get(key, {})
            existing_candles = existing_data.get('candles', [])
            
            if not existing_candles:
                pseudo_candle = {
                    'stat': 'Ok',
                    'time': msg.get('t', '00-00-0000 00:00:00'),
                    'into': msg['lp'], 'inth': msg.get('h', msg['lp']),
                    'intl': msg.get('l', msg['lp']), 'intc': msg['lp'],
                    'v': msg.get('v', '0'), 'ssboe': msg.get('ssboe', '0')
                }
                existing_candles = [pseudo_candle]
            else:
                existing_candles[-1]['intc'] = msg['lp']
                if float(msg.get('h', 0)) > float(existing_candles[-1]['inth']):
                    existing_candles[-1]['inth'] = msg['h']
                if float(msg.get('l', 0)) < float(existing_candles[-1]['intl']) and float(msg.get('l', 0)) > 0:
                    existing_candles[-1]['intl'] = msg['l']
            
            tick_data = {
                **msg, 'symbol': sym, 't': sym, 'company_name': self.get_company_name(tk, exchange=ex),
                'token': tk, 'exchange': ex, 'ltp': float(msg['lp']),
                'high': float(msg.get('h', 0)), 'low': float(msg.get('l', 0)), 'volume': int(msg.get('v', 0)),
                'candles': existing_candles
            }
            
            self.SYMBOLDICT[key] = tick_data
            
            full_symbol = sym.split('|')[-1] if '|' in sym else sym
            if f"{ex}|{full_symbol}" != key:
                self.SYMBOLDICT[f"{ex}|{full_symbol}"] = tick_data
            
            short_symbol = re.sub(r'\d{2}[A-Z]{3}\d{2}(FC|F)?$', '', full_symbol)
            if short_symbol != full_symbol and f"{ex}|{short_symbol}" != key:
                self.SYMBOLDICT[f"{ex}|{short_symbol}"] = tick_data
            
            for callback in self._tick_callbacks:
                try:
                    callback(sym, tick_data)
                except Exception as e:
                    self.logger.error(f"Tick callback error: {e}")
        
        connection.start_live_feed(resolved_symbols, _tick_handler)
        self.logger.info(f"[TickHandler] Live feed started for {len(symbols)} symbols.")
    
    def prime_candles(self, symbols: List[Any], lookback_mins: int = 300):
        """Prime SYMBOLDICT with historical candles from broker API."""
        self.logger.debug(f"[TickHandler] Priming {len(symbols)} symbols with last {lookback_mins} minutes data.")
        if not symbols: return
        
        from datetime import datetime, timedelta
        import pytz
        
        ist = pytz.timezone('Asia/Kolkata')
        end_dt = datetime.now(ist)
        start_dt = end_dt - timedelta(minutes=lookback_mins + 15)
        
        success_count = 0
        for item in symbols:
            try:
                token = ''
                exch = 'NSE'
                
                if isinstance(item, dict):
                    token = item.get('token', '')
                    token = str(token) if token else ''
                    
                    if token.isdigit():
                        exch = item.get('exchange', 'NSE')
                        key = f"{exch}|{token}"
                        ex, tk = key.split('|')
                        interval = getattr(self, '_priming_interval', 5)
                        res = self.api.get_time_price_series(
                            exchange=ex,
                            token=tk,
                            starttime=start_dt.timestamp(),
                            endtime=end_dt.timestamp(),
                            interval=interval
                        )
                        
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
                            self.logger.debug(f"[TickHandler] Primed {key} with {len(res)} candles.")
                        
                        import time
                        time.sleep(0.1)
                        continue
                
                import time
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"[TickHandler] Error priming {item}: {e}")
        
        self.logger.debug(f"[TickHandler] Primed {success_count}/{len(symbols)} symbols.")
    
    def _load_futures_map(self, exchange: str):
        """Load futures map for exchange."""
        path = os.path.join(self.project_root, 'orbiter', 'data', f'{exchange}_futures_map.json')
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"[TickHandler] Failed to load {exchange} futures_map: {e}")
        return None
