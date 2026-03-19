# orbiter/core/broker/broker_options_executor.py
"""
Broker Options Order Executor - real broker option trading.
"""

from typing import Dict
from orbiter.core.broker.options_executor import OptionsOrderExecutor


class BrokerOptionsOrderExecutor(OptionsOrderExecutor):
    """Real broker trading executor for options."""
    
    def __init__(self, api, master=None, resolver=None, execution_policy: Dict = None, 
                 project_root: str = None, segment_name: str = None):
        super().__init__(api, master, resolver, execution_policy, project_root, segment_name, paper_trade=False)
        self.logger.info("[BROKER_OPTIONS] BrokerOptionsOrderExecutor initialized")
    
    def place_option_order(self, option_details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Execute real broker option order."""
        tsym = option_details.get('tsym', option_details.get('symbol'))
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

        result = {**option_details, 'ok': True, 'resp': res, 'side': side}
        self.record_order(result)
        return result
    
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
