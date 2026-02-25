import unittest
import logging

from orbiter.core.broker.executor import OrderExecutor


class FakeApi:
    def __init__(self, quotes=None, order_ok=True):
        self.quotes = quotes or {}
        self.order_ok = order_ok
        self.orders = []

    def get_quotes(self, exchange=None, token=None):
        return self.quotes.get(str(token))

    def place_order(self, **kwargs):
        self.orders.append(kwargs)
        if self.order_ok:
            return {'stat': 'Ok', 'norenordno': '123'}
        return {'stat': 'Not_Ok', 'emsg': 'fail'}


class TestOrderExecutor(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("test_executor")

    def test_get_execution_params_override_and_default(self):
        policy = {
            'price_type_overrides': {'NIFTY': 'MKT'},
            'default_price_type': 'LMT'
        }
        ex = OrderExecutor(FakeApi(), self.logger, policy)

        price_type, order_price = ex._get_execution_params('NIFTY23FEBFUT', None)
        self.assertEqual(price_type, 'MKT')
        self.assertEqual(order_price, 0)

        price_type, _ = ex._get_execution_params('RECLTD', None)
        self.assertEqual(price_type, 'LMT')

    def test_place_future_order_dry_run(self):
        ex = OrderExecutor(FakeApi(), self.logger)
        res = ex.place_future_order({'tsym': 'RECLTDFUT', 'lot_size': 25}, side='B', execute=False, product_type='I', price_type='LMT')
        self.assertTrue(res['ok'])
        self.assertTrue(res['dry_run'])

    def test_place_future_order_limit_price(self):
        api = FakeApi(quotes={'123': {'lp': '100'}})
        policy = {'slippage_buffer_pct': 1.5}
        ex = OrderExecutor(api, self.logger, policy)

        res = ex.place_future_order({'tsym': 'RECLTDFUT', 'lot_size': 25, 'token': '123'}, side='B', execute=True, product_type='I', price_type='LMT')
        self.assertTrue(res['ok'])
        self.assertEqual(len(api.orders), 1)
        self.assertAlmostEqual(api.orders[0]['price'], 101.5, places=1)

    def test_place_spread_limit_price(self):
        quotes = {
            'ATM': {'lp': '200'},
            'HEDGE': {'lp': '50'}
        }
        api = FakeApi(quotes=quotes)
        policy = {'slippage_buffer_pct': 2.0, 'lot_size_overrides': {'RECLTD': 10}}
        ex = OrderExecutor(api, self.logger, policy)

        spread = {
            'atm_symbol': 'RECLTDATM',
            'hedge_symbol': 'RECLTDHEDGE',
            'lot_size': 25,
            'side': 'CALL',
            'atm_token': 'ATM',
            'hedge_token': 'HEDGE'
        }

        res = ex.place_spread(spread, execute=True, product_type='I', price_type='LMT')
        self.assertTrue(res['ok'])
        self.assertEqual(len(api.orders), 2)
        self.assertEqual(api.orders[0]['buy_or_sell'], 'B')
        self.assertEqual(api.orders[1]['buy_or_sell'], 'S')


if __name__ == '__main__':
    unittest.main()
