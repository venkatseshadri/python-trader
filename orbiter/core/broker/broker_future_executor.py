# orbiter/core/broker/broker_future_executor.py
"""
Broker Future Order Executor - real broker future trading.
"""

from typing import Dict
from orbiter.core.broker.future_executor import FutureOrderExecutor


class BrokerFutureOrderExecutor(FutureOrderExecutor):
    """Real broker trading executor for futures."""
    
    def __init__(self, api, master, resolver, execution_policy: Dict = None, 
                 project_root: str = None, segment_name: str = None):
        super().__init__(api, master, resolver, execution_policy, project_root, segment_name, paper_trade=False)
        self.logger.info("[BROKER_FUTURE] BrokerFutureOrderExecutor initialized")
    
    def _execute_future_order(self, details: Dict, side: str, execute: bool, product_type: str, price_type: str) -> Dict:
        """Execute real broker future order."""
        tsym = details['tsym']
        lot = details['lot_size']
        exch = details.get('exchange', 'NFO')
        side_name = "LONG" if side == 'B' else "SHORT"

        if not execute:
            self.logger.info(f"sim_order side={side} exchange={exch} symbol={tsym} qty={lot}")
            return {**details, 'dry_run': True, 'side': side, 'ok': True}

        price_type, order_price = self._get_execution_params(tsym, price_type)

        if price_type == 'LMT':
            try:
                q = self.api.get_quotes(exchange=exch, token=details.get('token'))
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
                                    retention='DAY', remarks=f'orb_future_{side_name}')
        self.logger.info(f"order_call side={side} exch={exch} sym={tsym} qty={lot} resp={res}")
        
        if not res or res.get('stat') != 'Ok': 
            return {'ok': False, 'reason': 'future_order_failed', 'resp': res}

        result = {**details, 'ok': True, 'resp': res, 'side': side}
        self.record_order(result)
        return result
