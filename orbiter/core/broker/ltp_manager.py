# orbiter/core/broker/ltp_manager.py
"""
LTP Manager - manages last traded prices from websocket ticks.
"""

import logging
from typing import Dict, Optional


class LTPManager:
    """Manages last traded prices from tick data."""
    
    def __init__(self, tick_handler):
        self.tick_handler = tick_handler
        self.logger = logging.getLogger("ltp_manager")
    
    def get_ltp(self, key: str) -> Optional[float]:
        """Get LTP from SYMBOLDICT by key."""
        return self.tick_handler.SYMBOLDICT.get(key, {}).get('ltp')
    
    def get_option_ltp_by_symbol(self, tsym: str, segment_name: str = None, master=None, api=None) -> Optional[float]:
        """Get option LTP by trading symbol."""
        self.logger.debug(f"[LTPManager] Getting option LTP for: {tsym}")
        
        if segment_name == 'mcx':
            for k, v in self.tick_handler.SYMBOLDICT.items():
                if v.get('symbol') == tsym:
                    return v.get('ltp')
        
        if master:
            for r in master.DERIVATIVE_OPTIONS:
                if r.get('tradingsymbol') == tsym:
                    self.logger.debug(f"[LTPManager] Found derivative option, fetching quotes.")
                    try:
                        q = api.get_quotes(exchange=r['exchange'], token=r['token'])
                        if q:
                            return float(q.get('lp') or q.get('ltp') or 0)
                    except Exception as e:
                        self.logger.error(f"[LTPManager] Error fetching quote: {e}")
                    return None
        
        self.logger.debug(f"[LTPManager] LTP not found for {tsym}.")
        return None
    
    def get_dk_levels(self, key: str) -> Dict:
        """Get DK levels (ltp, high, low) from SYMBOLDICT."""
        d = self.tick_handler.SYMBOLDICT.get(key, {})
        return {'ltp': d.get('ltp', 0), 'high': d.get('high', 0), 'low': d.get('low', 0)}
