import unittest
from types import SimpleNamespace
import time

from orbiter.core.engine.action.executor import ActionExecutor
from orbiter.core.engine.action.executors.equity import EquityActionExecutor, EquitySimulationExecutor
from orbiter.core.engine.action.executors.futures import FutureActionExecutor, FutureSimulationExecutor
from orbiter.core.engine.action.executors.options import OptionActionExecutor, OptionSimulationExecutor


class FakeAPI:
    def __init__(self):
        self.orders = []

    def place_order(self, **kwargs):
        self.orders.append(kwargs)
        return {'stat': 'Ok', 'orderid': '1'}


class FakeResolver:
    def resolve_option_symbol(self, symbol, ltp, option_type, strike_logic, expiry_type='current', exchange=None):
        return {
            'ok': True,
            'tradingsymbol': 'NIFTY26FEB25000CE',
            'exchange': 'NFO',
            'lot_size': 50
        }


class TestActionExecutors(unittest.TestCase):
    def test_equity_executor_live_and_sim(self):
        api = FakeAPI()
        client = SimpleNamespace(api=api, project_root='/Users/vseshadri/python')
        state = SimpleNamespace(client=client)

        ex = EquityActionExecutor(state)
        res = ex.execute(symbol='RECLTD', qty=2, price_type='MKT')
        self.assertEqual(res['stat'], 'Ok')
        self.assertEqual(api.orders[0]['tradingsymbol'], 'RECLTD')

        sim = EquitySimulationExecutor(state)
        res_sim = sim.execute(symbol='RECLTD', qty=1)
        self.assertTrue(res_sim['simulated'])

    def test_future_executor_resolve_and_fail(self):
        api = FakeAPI()

        def place_future_order_ok(**kwargs):
            return {'tsym': 'RECLTDFUT', 'exchange': 'NFO', 'lot_size': 25}

        client_ok = SimpleNamespace(api=api, place_future_order=place_future_order_ok, project_root='/Users/vseshadri/python')
        state_ok = SimpleNamespace(client=client_ok)

        ex = FutureActionExecutor(state_ok)
        res = ex.execute(symbol='RECLTD')
        self.assertEqual(res['stat'], 'Ok')
        self.assertEqual(api.orders[0]['tradingsymbol'], 'RECLTDFUT')

        def place_future_order_fail(**kwargs):
            return {}

        client_fail = SimpleNamespace(api=api, place_future_order=place_future_order_fail, project_root='/Users/vseshadri/python')
        state_fail = SimpleNamespace(client=client_fail)

        ex_fail = FutureActionExecutor(state_fail)
        res_fail = ex_fail.execute(symbol='RECLTD')
        self.assertIsNone(res_fail)

        sim = FutureSimulationExecutor(state_ok)
        res_sim = sim.execute(symbol='RECLTD')
        self.assertTrue(res_sim['simulated'])

    def test_option_executor_live_and_sim(self):
        api = FakeAPI()
        client = SimpleNamespace(
            api=api,
            segment_name='nfo',
            get_token=lambda symbol: 'NIFTY',
            get_ltp=lambda key: 25000,
            resolver=FakeResolver(),
            project_root='/Users/vseshadri/python'
        )
        state = SimpleNamespace(client=client)

        ex = OptionActionExecutor(state)
        res = ex.execute(symbol='NIFTY', option='CE', strike='ATM', side='B', qty_multiplier=2)
        self.assertEqual(res['stat'], 'Ok')
        self.assertEqual(api.orders[0]['quantity'], 100)

        sim = OptionSimulationExecutor(state)
        res_sim = sim.execute(symbol='NIFTY', option='CE', strike='ATM')
        self.assertTrue(res_sim['simulated'])


class TestOrderDeduplication(unittest.TestCase):
    def setUp(self):
        api = SimpleNamespace(
            place_order=lambda **kwargs: {'stat': 'Ok', 'orderid': '1'},
            get_quotes=lambda exchange, token: {'lp': 100.0}
        )
        client = SimpleNamespace(
            api=api,
            project_root='/Users/vseshadri/python',
            exchange_config={}
        )
        self.state = SimpleNamespace(
            client=client,
            config={'paper_trade': False}
        )
        self.executor = ActionExecutor(self.state)
        self.executor._order_ttl_seconds = 2  # 2 second TTL for testing

    def test_first_order_allowed(self):
        """First order should go through"""
        result = self.executor.place_order(symbol='RECLTD', side='B', execute=True)
        self.assertEqual(result['stat'], 'Ok')

    def test_duplicate_order_blocked(self):
        """Duplicate order within TTL should be blocked"""
        # First order
        self.executor.place_order(symbol='RECLTD', side='B', execute=True)
        
        # Second order same symbol+side - should be deduplicated
        result = self.executor.place_order(symbol='RECLTD', side='B', execute=True)
        self.assertTrue(result.get('deduplicated'))
        
        # Different side should be allowed
        result2 = self.executor.place_order(symbol='RECLTD', side='S', execute=True)
        self.assertEqual(result2['stat'], 'Ok')

    def test_order_after_ttl_allowed(self):
        """Order after TTL should go through"""
        # First order
        self.executor.place_order(symbol='RECLTD', side='B', execute=True)
        
        # Wait for TTL to expire
        time.sleep(2.5)
        
        # Should be allowed now
        result = self.executor.place_order(symbol='RECLTD', side='B', execute=True)
        self.assertEqual(result['stat'], 'Ok')


if __name__ == '__main__':
    unittest.main()
