# orbiter/utils/margin/margin_executor_base.py
"""
Base executor with actual order placement logic.
Used by MarginAwareExecutor to place orders after margin check passes.
"""

from typing import Dict, Any


class ExecutorBase:
    """Base executor with order placement logic."""
    
    def __init__(self, api, execution_policy: Dict = None):
        self.api = api
        self.execution_policy = execution_policy or {}
    
    def place_future_order(self, future_details: Dict, side: str, execute: bool, 
                          product_type: str, price_type: str) -> Dict:
        """Execute future order (actual broker call)."""
        tsym = future_details['tsym']
        lot = future_details['lot_size']
        exch = future_details.get('exchange', 'NFO')
        
        if not execute:
            return {**future_details, 'dry_run': True, 'side': side, 'ok': True}
        
        price_type, order_price = self._get_execution_params(tsym, price_type)
        
        if price_type == 'LMT':
            try:
                q = self.api.get_quotes(exchange=exch, token=future_details.get('token'))
                if not q or not q.get('lp'):
                    q = self.api.get_quotes(exchange=exch, token=tsym)
                order_price = float(q.get('lp', 0))
                
                if order_price == 0:
                    return {'ok': False, 'reason': f"limit_price_fetch_failed for {tsym}"}
                
                buffer = self.execution_policy.get('slippage_buffer_pct', 1.5) / 100.0
                if side == 'B':
                    order_price = round(order_price * (1 + buffer), 1)
                else:
                    order_price = round(order_price * (1 - buffer), 1)
            except Exception as e:
                return {'ok': False, 'reason': f"limit_price_error: {e}"}
        
        res = self.api.place_order(
            buy_or_sell=side,
            product_type=product_type,
            exchange=exch,
            tradingsymbol=tsym,
            quantity=lot,
            discloseqty=0,
            price_type=price_type,
            price=order_price,
            trigger_price=None,
            retention='DAY',
            remarks=f'orb_future_{side}'
        )
        
        if not res or res.get('stat') != 'Ok':
            return {'ok': False, 'reason': 'future_order_failed', 'resp': res}
        
        return {**future_details, 'ok': True, 'resp': res, 'side': side}
    
    def place_option_order(self, option_details: Dict, side: str, execute: bool, 
                          product_type: str, price_type: str) -> Dict:
        """Execute option order (actual broker call)."""
        tsym = option_details.get('tsym', option_details.get('symbol'))
        lot = option_details.get('lot_size', 1)
        exch = option_details.get('exchange', 'NFO')
        
        if not execute:
            return {**option_details, 'dry_run': True, 'side': side, 'ok': True}
        
        price_type, order_price = self._get_execution_params(tsym, price_type)
        
        if price_type == 'LMT':
            try:
                q = self.api.get_quotes(exchange=exch, token=option_details.get('token'))
                if not q or not q.get('lp'):
                    q = self.api.get_quotes(exchange=exch, token=tsym)
                order_price = float(q.get('lp', 0))
                
                if order_price == 0:
                    return {'ok': False, 'reason': f"limit_price_fetch_failed for {tsym}"}
                
                buffer = self.execution_policy.get('slippage_buffer_pct', 1.5) / 100.0
                if side == 'B':
                    order_price = round(order_price * (1 + buffer), 1)
                else:
                    order_price = round(order_price * (1 - buffer), 1)
            except Exception as e:
                return {'ok': False, 'reason': f"limit_price_error: {e}"}
        
        res = self.api.place_order(
            buy_or_sell=side,
            product_type=product_type,
            exchange=exch,
            tradingsymbol=tsym,
            quantity=lot,
            discloseqty=0,
            price_type=price_type,
            price=order_price,
            trigger_price=None,
            retention='DAY',
            remarks=f'orb_option_{side}'
        )
        
        if not res or res.get('stat') != 'Ok':
            return {'ok': False, 'reason': 'option_order_failed', 'resp': res}
        
        return {**option_details, 'ok': True, 'resp': res, 'side': side}
    
    def place_spread(self, spread: Dict, execute: bool, product_type: str, price_type: str) -> Dict:
        """Execute spread order (actual broker call)."""
        atm_sym = spread['atm_symbol']
        hedge_sym = spread['hedge_symbol']
        lot = spread['lot_size']
        exch = spread.get('exchange', 'NFO')
        side = spread.get('side', 'SHORT')
        
        if not execute:
            return {**spread, 'dry_run': True, 'ok': True}
        
        price_type, atm_price = self._get_execution_params(atm_sym, price_type)
        _, hedge_price = self._get_execution_params(hedge_sym, price_type)
        
        if price_type == 'LMT':
            try:
                h_q = self.api.get_quotes(exchange=exch, token=spread.get('hedge_token'))
                if not h_q or not h_q.get('lp'):
                    h_q = self.api.get_quotes(exchange=exch, token=hedge_sym)
                hedge_price = float(h_q.get('lp', 0))
                
                a_q = self.api.get_quotes(exchange=exch, token=spread.get('atm_token'))
                if not a_q or not a_q.get('lp'):
                    a_q = self.api.get_quotes(exchange=exch, token=atm_sym)
                atm_price = float(a_q.get('lp', 0))
                
                if atm_price == 0 or hedge_price == 0:
                    return {'ok': False, 'reason': f"limit_price_fetch_failed: atm={atm_price}, hedge={hedge_price}"}
                
                buffer = self.execution_policy.get('slippage_buffer_pct', 2.0) / 100.0
                hedge_price = round(hedge_price * (1 + buffer), 1)
                atm_price = round(atm_price * (1 - buffer), 1)
            except Exception as e:
                return {'ok': False, 'reason': f"limit_price_error: {e}"}
        
        h_res = self.api.place_order(
            buy_or_sell='B',
            product_type=product_type,
            exchange=exch,
            tradingsymbol=hedge_sym,
            quantity=lot,
            discloseqty=0,
            price_type=price_type,
            price=hedge_price,
            trigger_price=None,
            retention='DAY',
            remarks=f'orb_{side.lower()}_hedge'
        )
        
        if not h_res or h_res.get('stat') != 'Ok':
            return {'ok': False, 'reason': f"hedge_leg_failed: {h_res.get('emsg') if h_res else 'No response'}", 'resp': h_res}
        
        a_res = self.api.place_order(
            buy_or_sell='S',
            product_type=product_type,
            exchange=exch,
            tradingsymbol=atm_sym,
            quantity=lot,
            discloseqty=0,
            price_type=price_type,
            price=atm_price,
            trigger_price=None,
            retention='DAY',
            remarks=f'orb_{side.lower()}_atm'
        )
        
        if not a_res or a_res.get('stat') != 'Ok':
            return {'ok': False, 'reason': f"atm_leg_failed: {a_res.get('emsg') if a_res else 'No response'}", 'resp': a_res, 'hedge_order_id': h_res.get('norenordno')}
        
        return {**spread, 'ok': True, 'atm_resp': a_res, 'hedge_resp': h_res}
    
    def _get_execution_params(self, tsym: str, requested_price_type: str) -> tuple:
        """Resolve price_type and initial order_price based on policy."""
        price_type = requested_price_type
        
        overrides = self.execution_policy.get('price_type_overrides', {})
        for sym_key, p_type in overrides.items():
            if sym_key.upper() in tsym.upper():
                price_type = p_type
                break
        
        if not price_type:
            price_type = self.execution_policy.get('default_price_type', 'LMT')
        
        order_price = 0
        return price_type, order_price
