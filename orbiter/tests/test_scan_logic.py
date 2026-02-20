import unittest
from unittest.mock import MagicMock
from core.analytics.summary import SummaryManager

class TestScanLogic(unittest.TestCase):
    def setUp(self):
        # Mock BrokerClient
        self.mock_broker = MagicMock()
        self.summary = SummaryManager(self.mock_broker, 'nfo')
        
        # Mock State
        self.state = MagicMock()
        self.state.symbols = ['NFO|12345']
        # Mocking the filter results cache
        self.state.filter_results_cache = {
            'NFO|12345': {'f1': {'score': 10.5}}
        }

    def _get_report_for_prices(self, ltp, open_price, prev_close=None):
        """Helper to inject prices and get the report string"""
        self.mock_broker.get_symbol.return_value = "TESTSTOCK"
        self.state.client.SYMBOLDICT = {
            'NFO|12345': {
                'symbol': 'TESTSTOCK24FEB26F',
                'lp': str(ltp),
                'o': str(open_price),
                'pc': str(prev_close) if prev_close else '0'
            }
        }
        self.mock_broker.api.get_quotes.return_value = {'c': str(prev_close), 'lp': str(ltp)} if prev_close else {}
        self.mock_broker.get_token.return_value = 'NSE|12345'
        
        return self.summary.generate_live_scan_report(self.state)

    def test_valid_percentage(self):
        """Verify normal market moves are calculated correctly with new formatting."""
        report = self._get_report_for_prices(ltp=1050, prev_close=1000, open_price=1000)
        self.assertIn("<code>+5.00%</code>", report)
        self.assertIn("<code> +50.00</code>", report)
        self.assertIn("🟢 📈", report)

    def test_garbage_open_price(self):
        """Verify that baseline < 10.0 is caught."""
        report = self._get_report_for_prices(ltp=1050, open_price=1.0, prev_close=0)
        self.assertIn("<code>+0.00%</code>", report)
        self.assertIn("⚪ ➖", report)

    def test_impossible_move(self):
        """Verify that a >20% move is caught."""
        report = self._get_report_for_prices(ltp=1300, prev_close=1000, open_price=1000)
        self.assertIn("<code>+0.00%</code>", report)

    def test_zero_open_fallback_to_prev_close(self):
        """Verify fallback to previous close."""
        report = self._get_report_for_prices(ltp=1050, open_price=0, prev_close=1000)
        self.assertIn("<code>+5.00%</code>", report)

if __name__ == '__main__':
    unittest.main()
