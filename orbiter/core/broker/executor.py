import logging
from typing import Dict, Any

class OrderExecutor:
    def __init__(self, api, logger: logging.Logger):
        self.api = api
        self.logger = logger

    def place_future_order(self, future_details: Dict[str, Any], side: str, execute: bool, product_type: str, price_type: str) -> Dict[str, Any]:
        """Execute a single-leg Future order (Long or Short)"""
        tsym, lot = future_details['tsym'], future_details['lot_size']
        exch = future_details.get('exchange', 'NFO')
        side_name = "LONG" if side == 'B' else "SHORT"

        if not execute:
            self.logger.info(f"sim_order side={side} exchange={exch} symbol={tsym} qty={lot} product={product_type} remarks=orb_future_{side_name}")
            return {**future_details, 'dry_run': True, 'side': side, 'lot_size': lot}

        # Place Order
        res = self.api.place_order(buy_or_sell=side, product_type=product_type, exchange=exch, tradingsymbol=tsym, 
                                    quantity=lot, discloseqty=0, price_type=price_type, price=0, trigger_price=None, 
                                    retention='DAY', remarks=f'orb_future_{side_name}')
        self.logger.info(f"order_call side={side} exch={exch} sym={tsym} qty={lot} resp={res}")
        
        if not res or res.get('stat') != 'Ok': 
            return {'ok': False, 'reason': 'future_order_failed', 'resp': res}

        return {**future_details, 'ok': True, 'resp': res, 'side': side}
