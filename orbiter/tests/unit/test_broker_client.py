import unittest
from unittest.mock import patch

import orbiter.core.broker as broker_mod


class FakeAPI:
    def __init__(self):
        self.time_series = [
            {'intc': '100', 'inth': '110', 'intl': '90', 'v': '1000'}
        ]
        self.quotes = {
            'OPT1': {'lp': '123'}
        }

    def get_time_price_series(self, exchange=None, token=None, starttime=None, endtime=None, interval=None):
        return list(self.time_series)

    def get_quotes(self, exchange=None, token=None):
        return self.quotes.get(str(token))

    def get_limits(self):
        return {
            'stat': 'Ok',
            'cash': '1000',
            'collateral': '2000',
            'marginused': '500',
            'payin': '0'
        }

    def get_positions(self):
        return [{'stat': 'Ok', 'tsym': 'RECLTD'}]

    def get_order_book(self):
        return [{'stat': 'Ok', 'orderid': '1'}]


class FakeConnectionManager:
    def __init__(self, config_path):
        self.api = FakeAPI()
        self.cred = {'user': 'U'}
        self.closed = False

    def login(self, factor2_override=None):
        return True

    def start_live_feed(self, symbols, on_tick_callback):
        msg = {'lp': '100', 'tk': '123', 'e': 'NSE', 'h': '110', 'l': '90', 'v': '1000'}
        on_tick_callback(msg, '123', 'NSE')

    def close(self):
        self.closed = True


class FakeScripMaster:
    def __init__(self, project_root):
        self.TOKEN_TO_SYMBOL = {'123': 'RECLTD'}
        self.SYMBOL_TO_TOKEN = {'RECLTD': '123'}
        self.TOKEN_TO_COMPANY = {'123': 'RECLTD LTD'}
        self.TOKEN_TO_LOTSIZE = {'123': 25}
        self.DERIVATIVE_OPTIONS = [
            {'tradingsymbol': 'RECLTD26MAR500CE', 'exchange': 'NFO', 'token': 'OPT1'}
        ]
        self.DERIVATIVE_LOADED = True
        self.load_calls = []
        self.download_calls = []

    def load_mappings(self, segment_name):
        self.load_calls.append(segment_name)

    def download_scrip_master(self, exchange):
        self.download_calls.append(exchange)

    def load_segment_futures_map(self, segment_name):
        pass


class TestBrokerClient(unittest.TestCase):
    def _make_client(self):
        with patch.object(broker_mod, 'ConnectionManager', FakeConnectionManager), \
             patch.object(broker_mod, 'ScripMaster', FakeScripMaster), \
             patch('orbiter.utils.data_manager.DataManager.load_config', return_value={'nfo': {'execution_policy': {}}}):
            broker_mod.BrokerClient._SHARED_MASTER = None
            return broker_mod.BrokerClient(project_root='/Users/vseshadri/python', config_path='cred.yml', segment_name='nfo')

    def test_init_and_properties(self):
        client = self._make_client()
        self.assertEqual(client.segment_name, 'nfo')
        self.assertEqual(client.TOKEN_TO_SYMBOL.get('123'), 'RECLTD')

    def test_start_live_feed_updates_symboldict(self):
        client = self._make_client()
        client.start_live_feed(['NSE|123'])
        self.assertIn('NSE|123', client.SYMBOLDICT)
        self.assertEqual(client.SYMBOLDICT['NSE|123']['ltp'], 100.0)

    def test_prime_candles(self):
        client = self._make_client()
        client.prime_candles(['RECLTD'], lookback_mins=1)
        self.assertIn('NSE|123', client.SYMBOLDICT)
        self.assertTrue(client.SYMBOLDICT['NSE|123']['candles'])

    def test_get_option_ltp_by_symbol(self):
        client = self._make_client()
        ltp = client.get_option_ltp_by_symbol('RECLTD26MAR500CE')
        self.assertEqual(ltp, 123.0)

    def test_get_limits_positions_orders(self):
        client = self._make_client()
        limits = client.get_limits()
        self.assertIsNotNone(limits)
        self.assertIn('available', limits)

        positions = client.get_positions()
        self.assertEqual(len(positions), 1)

        orders = client.get_order_history()
        self.assertEqual(len(orders), 1)


if __name__ == '__main__':
    unittest.main()
