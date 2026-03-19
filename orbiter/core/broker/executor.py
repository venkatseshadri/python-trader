# orbiter/core/broker/executor.py
"""
Order Executor Interface for Orbiter.

Provides abstract interface for order execution with two implementations:
- PaperOrderExecutor: Simulated trading with margin checks
- BrokerOrderExecutor: Real broker trading
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any


class OrderExecutorInterface(ABC):
    """Abstract interface for order execution."""
    
    @abstractmethod
    def place_future_order(self, future_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Place a future order."""
        pass
    
    @abstractmethod
    def place_option_order(self, option_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Place an option order."""
        pass
    
    @abstractmethod
    def place_spread(self, spread_details: Dict, execute: bool, product_type: str, price_type: str) -> Dict:
        """Place a spread order (multi-leg)."""
        pass


class PaperOrderExecutor(OrderExecutorInterface):
    """Paper trading executor with margin checks."""
    
    def __init__(self, api, logger_instance, execution_policy: Dict = None):
        self.api = api
        self.logger = logger_instance
        self.execution_policy = execution_policy or {}
        
        from orbiter.utils.margin.margin_executor import MarginAwareExecutor
        self._executor = MarginAwareExecutor(
            api,
            logger_instance,
            execution_policy=execution_policy,
            paper_trade=True
        )
        self.logger.info("[PAPER] PaperOrderExecutor initialized with margin checks")
    
    def place_future_order(self, future_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        return self._executor.place_future_order(future_details, side, execute, product_type, price_type)
    
    def place_option_order(self, option_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        return self._executor.place_option_order(option_details, side, execute, product_type, price_type)
    
    def place_spread(self, spread_details: Dict, execute: bool, product_type: str, price_type: str) -> Dict:
        return self._executor.place_spread(spread_details, execute, product_type, price_type)


class BrokerOrderExecutor(OrderExecutorInterface):
    """Real broker trading executor."""
    
    def __init__(self, api, logger_instance, execution_policy: Dict = None):
        self.api = api
        self.logger = logger_instance
        self.policy = execution_policy or {}
        self.logger.info("[BROKER] BrokerOrderExecutor initialized for live trading")

    def _get_execution_params(self, tsym: str, requested_price_type: str) -> tuple:
        """Resolves price_type and initial order_price based on policy."""
        price_type = requested_price_type
        
        overrides = self.policy.get('price_type_overrides', {})
        for sym_key, p_type in overrides.items():
            if sym_key.upper() in tsym.upper():
                price_type = p_type
                break
        
        if not price_type:
            price_type = self.policy.get('default_price_type', 'LMT')
            
        order_price = 0
        return price_type, order_price

    def place_future_order(self, future_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Execute a single-leg Future order (Long or Short)"""
        tsym, lot = future_details['tsyn'], future_details['lot_size']
        exch = future_details.get('exchange', 'NFO')
        side_name = "LONG" if side == 'B' else "SHORT"

        if not execute:
            self.logger.info(f"sim_order side={side} exchange={exch} symbol={tsyn} qty={lot} product={product_type} remarks=orb_future_{side_name}")
            return {**future_details, 'dry_run': True, 'side': side, 'lot_size': lot, 'ok': True}

        price_type, order_price = self._get_execution_params(tsyn, price_type)

        if price_type == 'LMT':
            try:
                q = self.api.get_quotes(exchange=exch, token=future_details.get('token'))
                if not q or not q.get('lp'):
                    q = self.api.get_quotes(exchange=exch, token=tsyn)
                order_price = float(q.get('lp', 0))
                
                if order_price == 0:
                    return {'ok': False, 'reason': f"limit_price_fetch_failed for {tsyn}"}
                
                buffer = self.policy.get('slippage_buffer_pct', 1.5) / 100.0
                if side == 'B': order_price = round(order_price * (1 + buffer), 1)
                else: order_price = round(order_price * (1 - buffer), 1)
            except Exception as e:
                return {'ok': False, 'reason': f"limit_price_error: {e}"}

        res = self.api.place_order(buy_or_sell=side, product_type=product_type, exchange=exch, tradingsymbol=tsyn, 
                                    quantity=lot, discloseqty=0, price_type=price_type, price=order_price, trigger_price=None, 
                                    retention='DAY', remarks=f'orb_future_{side_name}')
        self.logger.info(f"order_call side={side} exch={exch} sym={tsyn} qty={lot} resp={res} limit={order_price}")
        
        if not res or res.get('stat') != 'Ok': 
            return {'ok': False, 'reason': 'future_order_failed', 'resp': res}

        return {**future_details, 'ok': True, 'resp': res, 'side': side}

    def place_option_order(self, option_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Place an option order - delegates to place_spread for spreads or single option."""
        # For single option orders, use similar logic as place_future_order
        tsym = option_details.get('tsyn', option_details.get('symbol'))
        lot = option_details.get('lot_size', 1)
        exch = option_details.get('exchange', 'NFO')
        side_name = "LONG" if side == 'B' else "SHORT"

        if not execute:
            self.logger.info(f"sim_option side={side} exchange={exch} symbol={tsym} qty={lot} product={product_type}")
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
                
                buffer = self.policy.get('slippage_buffer_pct', 1.5) / 100.0
                if side == 'B': order_price = round(order_price * (1 + buffer), 1)
                else: order_price = round(order_price * (1 - buffer), 1)
            except Exception as e:
                return {'ok': False, 'reason': f"limit_price_error: {e}"}

        res = self.api.place_order(buy_or_sell=side, product_type=product_type, exchange=exch, tradingsymbol=tsym, 
                                    quantity=lot, discloseqty=0, price_type=price_type, price=order_price, trigger_price=None, 
                                    retention='DAY', remarks=f'orb_option_{side_name}')
        self.logger.info(f"order_call side={side} exch={exch} sym={tsym} qty={lot} resp={res}")
        
        if not res or res.get('stat') != 'Ok': 
            return {'ok': False, 'reason': 'option_order_failed', 'resp': res}

        return {**option_details, 'ok': True, 'resp': res, 'side': side}

    def place_spread(self, spread: Dict, execute: bool, product_type: str, price_type: str) -> Dict:
        """Execute a two-leg Option Credit Spread (Sell ATM, Buy Hedge)"""
        atm_sym = spread['atm_symbol']
        hedge_sym = spread['hedge_symbol']
        lot = spread['lot_size']
        
        lot_overrides = self.policy.get('lot_size_overrides', {})
        for sym_key, forced_lot in lot_overrides.items():
            if sym_key.upper() in atm_sym.upper():
                lot = forced_lot
                self.logger.info(f"Safety Override: Forcing {sym_key} lot to {lot}")
                break

        exch = spread.get('exchange', 'NFO')
        side = spread['side']

        if not execute:
            self.logger.info(f"sim_spread side={side} atm={atm_sym} hedge={hedge_sym} qty={lot} product={product_type}")
            return {**spread, 'dry_run': True}

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
                
                buffer = self.policy.get('slippage_buffer_pct', 2.0) / 100.0
                hedge_price = round(hedge_price * (1 + buffer), 1)
                atm_price = round(atm_price * (1 - buffer), 1)
            except Exception as e:
                return {'ok': False, 'reason': f"limit_price_error: {e}"}

        h_res = self.api.place_order(buy_or_sell='B', product_type=product_type, exchange=exch, tradingsymbol=hedge_sym,
                                    quantity=lot, discloseqty=0, price_type=price_type, price=hedge_price, trigger_price=None,
                                    retention='DAY', remarks=f'orb_{side.lower()}_hedge')
        self.logger.info(f"order_call side=B exch={exch} sym={hedge_sym} qty={lot} resp={h_res}")

        if not h_res or h_res.get('stat') != 'Ok':
             return {'ok': False, 'reason': f"hedge_leg_failed: {h_res.get('emsg') if h_res else 'No response'}", 'resp': h_res}

        a_res = self.api.place_order(buy_or_sell='S', product_type=product_type, exchange=exch, tradingsymbol=atm_sym,
                                    quantity=lot, discloseqty=0, price_type=price_type, price=atm_price, trigger_price=None,
                                    retention='DAY', remarks=f'orb_{side.lower()}_atm')
        self.logger.info(f"order_call side=S exch={exch} sym={atm_sym} qty={lot} resp={a_res}")

        if not a_res or a_res.get('stat') != 'Ok':
             return {'ok': False, 'reason': f"atm_leg_failed: {a_res.get('emsg') if a_res else 'No response'}", 'resp': a_res, 'hedge_order_id': h_res.get('norenordno')}

        return {**spread, 'ok': True, 'atm_resp': a_res, 'hedge_resp': h_res}


def create_executor(api, logger_instance, real_broker_trade: bool, execution_policy: Dict = None) -> OrderExecutorInterface:
    """Factory function to create the appropriate executor."""
    if real_broker_trade:
        return BrokerOrderExecutor(api, logger_instance, execution_policy)
    else:
        return PaperOrderExecutor(api, logger_instance, execution_policy)
