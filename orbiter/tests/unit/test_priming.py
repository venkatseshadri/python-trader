import unittest
from unittest.mock import MagicMock, patch
from orbiter.core.broker import BrokerClient

class TestAutomaticPriming(unittest.TestCase):
    @patch('orbiter.core.broker.ConnectionManager')
    @patch('orbiter.core.broker.ScripMaster')
    def test_prime_candles_success(self, mock_master, mock_conn):
        from orbiter.utils.constants_manager import ConstantsManager
        ConstantsManager._instance = None
        client = BrokerClient()
        client.conn.api = MagicMock()
        
        # Mock API response for get_time_price_series
        mock_candles = [
            {'intc': '100', 'inth': '105', 'intl': '95', 'v': '1000', 'stat': 'Ok'},
            {'intc': '101', 'inth': '106', 'intl': '96', 'v': '1100', 'stat': 'Ok'}
        ]
        client.api.get_time_price_series.return_value = mock_candles
        
        symbols = ["NSE|123"]
        client.prime_candles(symbols)
        
        # Verify SYMBOLDICT is primed
        self.assertIn("NSE|123", client.SYMBOLDICT)
        self.assertEqual(len(client.SYMBOLDICT["NSE|123"]["candles"]), 2)
        self.assertEqual(client.SYMBOLDICT["NSE|123"]["ltp"], 101.0)

if __name__ == "__main__":
    unittest.main()
