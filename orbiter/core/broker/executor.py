import logging
from typing import Dict, Any

class OrderExecutor:
    def __init__(self, api, logger: logging.Logger, execution_policy: Dict[str, Any] = None):
        self.api = api
        self.logger = logger
        self.policy = execution_policy or {}

    def _get_execution_params(self, tsym: str, requested_price_type: str) -> tuple:
        """Resolves price_type and initial order_price based on policy."""
        price_type = requested_price_type
        
        # 1. Price Type Overrides (e.g., NIFTY -> MKT)
        overrides = self.policy.get('price_type_overrides', {})
        for sym_key, p_type in overrides.items():
            if sym_key.upper() in tsym.upper():
                price_type = p_type
                break
        
        # 2. Fallback to default if not overridden
        if not price_type:
            price_type = self.policy.get('default_price_type', 'LMT')
            
        order_price = 0
        return price_type, order_price

    def place_future_order(self, future_details: Dict[str, Any], side: str, execute: bool, product_type: str, price_type: str) -> Dict[str, Any]:
        """Execute a single-leg Future order (Long or Short)"""
        tsym, lot = future_details['tsym'], future_details['lot_size']
        exch = future_details.get('exchange', 'NFO')
        side_name = "LONG" if side == 'B' else "SHORT"

        if not execute:
            self.logger.info(f"sim_order side={side} exchange={exch} symbol={tsym} qty={lot} product={product_type} remarks=orb_future_{side_name}")
            return {**future_details, 'dry_run': True, 'side': side, 'lot_size': lot, 'ok': True}

        # Resolve Execution Policy
        price_type, order_price = self._get_execution_params(tsym, price_type)

        # 1. Resolve Limit Price if needed
        if price_type == 'LMT':
            try:
                q = self.api.get_quotes(exchange=exch, token=future_details.get('token'))
                if not q or not q.get('lp'):
                    q = self.api.get_quotes(exchange=exch, token=tsym)
                order_price = float(q.get('lp', 0))
                
                if order_price == 0:
                    return {'ok': False, 'reason': f"limit_price_fetch_failed for {tsym}"}
                
                # Slippage Buffer from Policy (default 1.5%)
                buffer = self.policy.get('slippage_buffer_pct', 1.5) / 100.0
                if side == 'B': order_price = round(order_price * (1 + buffer), 1)
                else: order_price = round(order_price * (1 - buffer), 1)
            except Exception as e:
                return {'ok': False, 'reason': f"limit_price_error: {e}"}

        # Place Order
        res = self.api.place_order(buy_or_sell=side, product_type=product_type, exchange=exch, tradingsymbol=tsym, 
                                    quantity=lot, discloseqty=0, price_type=price_type, price=order_price, trigger_price=None, 
                                    retention='DAY', remarks=f'orb_future_{side_name}')
        self.logger.info(f"order_call side={side} exch={exch} sym={tsym} qty={lot} resp={res} limit={order_price}")
        
        if not res or res.get('stat') != 'Ok': 
            return {'ok': False, 'reason': 'future_order_failed', 'resp': res}

        return {**future_details, 'ok': True, 'resp': res, 'side': side}

    def place_spread(self, spread: Dict[str, Any], execute: bool, product_type: str, price_type: str) -> Dict[str, Any]:
        """Execute a two-leg Option Credit Spread (Sell ATM, Buy Hedge)"""
        atm_sym = spread['atm_symbol']
        hedge_sym = spread['hedge_symbol']
        lot = spread['lot_size']
        
        # 🔥 Dynamic Lot Size Overrides from Policy
        lot_overrides = self.policy.get('lot_size_overrides', {})
        for sym_key, forced_lot in lot_overrides.items():
            if sym_key.upper() in atm_sym.upper():
                lot = forced_lot
                self.logger.info(f"🛡️ Safety Override: Forcing {sym_key} lot to {lot}")
                break

        exch = spread.get('exchange', 'NFO')
        side = spread['side'] # 'PUT' or 'CALL'

        if not execute:
            self.logger.info(f"sim_spread side={side} atm={atm_sym} hedge={hedge_sym} qty={lot} product={product_type}")
            return {**spread, 'dry_run': True}

        # Resolve Execution Policy
        price_type, atm_price = self._get_execution_params(atm_sym, price_type)
        _, hedge_price = self._get_execution_params(hedge_sym, price_type)

        # 1. Resolve Limit Prices if needed
        if price_type == 'LMT':
            try:
                # Hedge Leg
                h_q = self.api.get_quotes(exchange=exch, token=spread.get('hedge_token'))
                if not h_q or not h_q.get('lp'):
                    h_q = self.api.get_quotes(exchange=exch, token=hedge_sym)
                hedge_price = float(h_q.get('lp', 0))

                # ATM Leg
                a_q = self.api.get_quotes(exchange=exch, token=spread.get('atm_token'))
                if not a_q or not a_q.get('lp'):
                    a_q = self.api.get_quotes(exchange=exch, token=atm_sym)
                atm_price = float(a_q.get('lp', 0))
                
                if atm_price == 0 or hedge_price == 0:
                    return {'ok': False, 'reason': f"limit_price_fetch_failed: atm={atm_price}, hedge={hedge_price}"}
                
                # Slippage Buffer from Policy (default 2%)
                buffer = self.policy.get('slippage_buffer_pct', 2.0) / 100.0
                hedge_price = round(hedge_price * (1 + buffer), 1) # Buy higher
                atm_price = round(atm_price * (1 - buffer), 1)    # Sell lower
            except Exception as e:
                return {'ok': False, 'reason': f"limit_price_error: {e}"}

        # 2. BUY Hedge first for margin benefit
        h_res = self.api.place_order(buy_or_sell='B', product_type=product_type, exchange=exch, tradingsymbol=hedge_sym,
                                    quantity=lot, discloseqty=0, price_type=price_type, price=hedge_price, trigger_price=None,
                                    retention='DAY', remarks=f'orb_{side.lower()}_hedge')
        self.logger.info(f"order_call side=B exch={exch} sym={hedge_sym} qty={lot} resp={h_res} limit={hedge_price}")

        if not h_res or h_res.get('stat') != 'Ok':
             return {'ok': False, 'reason': f"hedge_leg_failed: {h_res.get('emsg') if h_res else 'No response'}", 'resp': h_res}

        # 3. SELL ATM
        a_res = self.api.place_order(buy_or_sell='S', product_type=product_type, exchange=exch, tradingsymbol=atm_sym,
                                    quantity=lot, discloseqty=0, price_type=price_type, price=atm_price, trigger_price=None,
                                    retention='DAY', remarks=f'orb_{side.lower()}_atm')
        self.logger.info(f"order_call side=S exch={exch} sym={atm_sym} qty={lot} resp={a_res} limit={atm_price}")

        if not a_res or a_res.get('stat') != 'Ok':
             return {'ok': False, 'reason': f"atm_leg_failed: {a_res.get('emsg') if a_res else 'No response'}", 'resp': a_res, 'hedge_order_id': h_res.get('norenordno')}

        return {**spread, 'ok': True, 'atm_resp': a_res, 'hedge_resp': h_res}
