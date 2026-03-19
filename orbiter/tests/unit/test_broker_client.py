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
    def __init__(self, config_path=None):
        self.api = FakeAPI()
        self.cred = {'user': 'U'}
        self.closed = False
        self.tick_handler = FakeTickHandler(self.api)

    def login(self, factor2_override=None):
        return True

    def start_live_feed(self, symbols, on_tick_callback):
        msg = {'lp': '100', 'tk': '123', 'e': 'NSE', 'h': '110', 'l': '90', 'v': '1000'}
        on_tick_callback(msg, '123', 'NSE')

    def close(self):
        self.closed = True


class FakeTickHandler:
    def __init__(self, api):
        self.api = api
        self.SYMBOLDICT = {}
        self._priming_interval = 5
    
    def start_live_feed(self, conn, symbols):
        msg = {'lp': '100', 'tk': '123', 'e': 'NSE', 'h': '110', 'l': '90', 'v': '1000'}
        self._on_tick({'lp': '100', 'tk': '123', 'e': 'NSE', 'h': '110', 'l': '90', 'v': '1000'}, '123', 'NSE')
    
    def _on_tick(self, msg, tk, ex):
        key = f"{ex}|{tk}"
        self.SYMBOLDICT[key] = {
            'symbol': f'{ex}|{tk}', 'ltp': float(msg.get('lp', 0)),
            'high': float(msg.get('h', 0)), 'low': float(msg.get('l', 0)),
            'volume': int(msg.get('v', 0)), 'candles': []
        }
    
    def prime_candles(self, symbols, lookback_mins=300):
        self.SYMBOLDICT['NSE|123'] = {
            'symbol': 'NSE|123', 'ltp': 100.0, 'high': 110.0, 'low': 90.0,
            'volume': 1000, 'candles': [{'intc': 100, 'inth': 110, 'intl': 90}]
        }
    
    @property
    def ltp_manager(self):
        return FakeLTPManager(self)


class FakeLTPManager:
    def __init__(self, tick_handler):
        self.tick_handler = tick_handler
    
    def get_ltp(self, key):
        return self.tick_handler.SYMBOLDICT.get(key, {}).get('ltp')
    
    def get_option_ltp_by_symbol(self, tsym, segment_name=None, master=None, api=None):
        return 123.0
    
    def get_dk_levels(self, key):
        return self.tick_handler.SYMBOLDICT.get(key, {'ltp': 0, 'high': 0, 'low': 0})


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
            broker_mod.BrokerClient._MASTERS = {}
            return broker_mod.BrokerClient(project_root='/Users/vseshadri/python', segment_name='nfo')

    def test_init_and_properties(self):
        client = self._make_client()
        self.assertEqual(client.segment_name, 'nfo')
        self.assertEqual(client.master.TOKEN_TO_SYMBOL.get('123'), 'RECLTD')

    def test_start_live_feed_updates_symboldict(self):
        client = self._make_client()
        client.conn.tick_handler.start_live_feed(client.conn, ['NSE|123'])
        self.assertIn('NSE|123', client.conn.tick_handler.SYMBOLDICT)
        self.assertEqual(client.conn.tick_handler.SYMBOLDICT['NSE|123']['ltp'], 100.0)

    def test_prime_candles(self):
        client = self._make_client()
        client.conn.tick_handler.prime_candles([{'token': '123', 'exchange': 'NSE'}], lookback_mins=1)
        self.assertIn('NSE|123', client.conn.tick_handler.SYMBOLDICT)
        self.assertTrue(client.conn.tick_handler.SYMBOLDICT['NSE|123']['candles'])

    def test_get_option_ltp_by_symbol(self):
        client = self._make_client()
        ltp = client.conn.tick_handler.ltp_manager.get_option_ltp_by_symbol('RECLTD26MAR500CE', 'nfo', client.master, client.conn.api)
        self.assertEqual(ltp, 123.0)

    def test_get_limits_positions_orders(self):
        client = self._make_client()
        limits = client.margin.get_limits()
        self.assertIsNotNone(limits)

        positions = client.executor.get_positions()
        self.assertIsInstance(positions, list)

        orders = client.executor.get_order_history()
        self.assertIsInstance(orders, list)


if __name__ == '__main__':
    unittest.main()
