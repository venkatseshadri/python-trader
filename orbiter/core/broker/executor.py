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
            return {**future_details, 'dry_run': True, 'side': side, 'lot_size': lot, 'ok': True}

        # Place Order
        res = self.api.place_order(buy_or_sell=side, product_type=product_type, exchange=exch, tradingsymbol=tsym, 
                                    quantity=lot, discloseqty=0, price_type=price_type, price=0, trigger_price=None, 
                                    retention='DAY', remarks=f'orb_future_{side_name}')
        self.logger.info(f"order_call side={side} exch={exch} sym={tsym} qty={lot} resp={res}")
        
        if not res or res.get('stat') != 'Ok': 
            return {'ok': False, 'reason': 'future_order_failed', 'resp': res}

        return {**future_details, 'ok': True, 'resp': res, 'side': side}

    def place_spread(self, spread: Dict[str, Any], execute: bool, product_type: str, price_type: str) -> Dict[str, Any]:
        """Execute a two-leg Option Credit Spread (Sell ATM, Buy Hedge)"""
        atm_sym = spread['atm_symbol']
        hedge_sym = spread['hedge_symbol']
        lot = spread['lot_size']
        
        # 🔥 SAFETY GASKET (v3.15.0)
        # Force exactly 1 lot for NIFTY Index (75 shares) to prevent over-leverage
        if 'NIFTY' in atm_sym.upper():
            lot = 75
            print(f"🛡️ NIFTY Safety: Forcing exactly 1 lot ({lot} shares)")

        exch = spread.get('exchange', 'NFO')
        side = spread['side'] # 'PUT' or 'CALL'

        if not execute:
            self.logger.info(f"sim_spread side={side} atm={atm_sym} hedge={hedge_sym} qty={lot} product={product_type}")
            return {**spread, 'dry_run': True}

        # 1. BUY Hedge first for margin benefit
        h_res = self.api.place_order(buy_or_sell='B', product_type=product_type, exchange=exch, tradingsymbol=hedge_sym,
                                    quantity=lot, discloseqty=0, price_type=price_type, price=0, trigger_price=None,
                                    retention='DAY', remarks=f'orb_{side.lower()}_hedge')
        self.logger.info(f"order_call side=B exch={exch} sym={hedge_sym} qty={lot} resp={h_res}")

        if not h_res or h_res.get('stat') != 'Ok':
             return {'ok': False, 'reason': f"hedge_leg_failed: {h_res.get('emsg') if h_res else 'No response'}", 'resp': h_res}

        # 2. SELL ATM
        a_res = self.api.place_order(buy_or_sell='S', product_type=product_type, exchange=exch, tradingsymbol=atm_sym,
                                    quantity=lot, discloseqty=0, price_type=price_type, price=0, trigger_price=None,
                                    retention='DAY', remarks=f'orb_{side.lower()}_atm')
        self.logger.info(f"order_call side=S exch={exch} sym={atm_sym} qty={lot} resp={a_res}")

        if not a_res or a_res.get('stat') != 'Ok':
             return {'ok': False, 'reason': f"atm_leg_failed: {a_res.get('emsg') if a_res else 'No response'}", 'resp': a_res, 'hedge_order_id': h_res.get('norenordno')}

        return {**spread, 'ok': True, 'atm_resp': a_res, 'hedge_resp': h_res}
