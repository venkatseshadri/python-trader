import unittest
from unittest.mock import MagicMock, patch
from orbiter.core.broker import BrokerClient
from orbiter.core.broker.master import ScripMaster

class TestBrokerFacade(unittest.TestCase):

    @patch('orbiter.core.broker.ConnectionManager')
    def setUp(self, mock_conn):
        self.mock_conn = mock_conn
        # Initialize BrokerClient with mocked connection
        self.client = BrokerClient(config_path='fake.yml', segment_name='nfo')

    def test_client_delegation(self):
        """Verify BrokerClient delegates calls correctly"""
        # Test get_symbol
        self.client.master.TOKEN_TO_SYMBOL = {'123': 'TEST-SYM'}
        self.assertEqual(self.client.get_symbol('123'), 'TEST-SYM')
        
        # Test login
        self.client.login()
        self.client.conn.login.assert_called_once()

    def test_scrip_master_parsing(self):
        """Verify scrip master date parsing logic"""
        master = ScripMaster()
        # Test various formats
        d1 = master._parse_expiry_date('26-FEB-2026')
        self.assertEqual(d1.year, 2026)
        
        d2 = master._parse_expiry_date('2026-02-26')
        self.assertEqual(d2.month, 2)

    def test_token_resolution_logic(self):
        """Verify dual-key token resolution in ScripMaster facade pointers"""
        master = ScripMaster()
        # Mock values directly into managers since ScripMaster links to them
        master.equity.TOKEN_TO_SYMBOL['12345'] = 'SBIN-EQ'
        
        # Should work via pointer
        self.assertEqual(master.TOKEN_TO_SYMBOL.get('12345'), 'SBIN-EQ')

    def test_dual_key_loading(self):
        """Verify that load_segment_futures_map implements Dual-Key storage"""
        with patch('os.path.exists', return_value=True), \
             patch('builtins.open', unittest.mock.mock_open(read_data='{"477167": ["COPPER", "COPPER27FEB26", "2500"]}')):
            master = ScripMaster()
            master.load_segment_futures_map(segment_name='mcx')
            
            # 1. Raw Key
            self.assertEqual(master.TOKEN_TO_SYMBOL.get('477167'), 'COPPER27FEB26')
            # 2. Prefixed Key
            self.assertEqual(master.TOKEN_TO_SYMBOL.get('MCX|477167'), 'COPPER27FEB26')
            # 3. Lot Size
            self.assertEqual(master.TOKEN_TO_LOTSIZE.get('MCX|477167'), 2500)

    @patch('requests.get')
    def test_scrip_master_download_proxy(self, mock_get):
        """Verify downloader proxy call"""
        with patch.dict('os.environ', {'ORBITER_TEST_MODE': '0'}):
            master = ScripMaster()
            # Mock the internal download methods to avoid full zip parsing in this unit test
            master._download_nse = MagicMock()
            master._download_derivative_exchange = MagicMock()
            
            master.download_scrip_master("NSE")
            master._download_nse.assert_called_once()
            
            master.download_scrip_master("NFO")
            master._download_derivative_exchange.assert_called_with("NFO")

    def test_client_facade_methods(self):
        """Verify BrokerClient facade methods return correct data"""
        self.client.api.get_limits.return_value = {'stat': 'Ok', 'cash': '10000', 'collateral': '5000', 'marginused': '2000'}
        limits = self.client.get_limits()
        self.assertEqual(limits['liquid_cash'], 10000.0)
        self.assertEqual(limits['available'], 13000.0)

        self.client.api.get_positions.return_value = [{'stat': 'Ok', 'tsym': 'SBIN'}]
        pos = self.client.get_positions()
        self.assertEqual(len(pos), 1)

        self.client.api.get_order_book.return_value = [{'stat': 'Ok', 'norenordno': '1'}]
        orders = self.client.get_order_history()
        self.assertEqual(len(orders), 1)

if __name__ == '__main__':
    unittest.main()
