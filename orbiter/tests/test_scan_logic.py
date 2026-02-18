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
        # Mocking the filter results cache to have one entry
        self.state.filter_results_cache = {
            'NFO|12345': {'f1': {'score': 10.5}}
        }

    def _get_report_for_prices(self, ltp, open_price, prev_close=None):
        """Helper to inject prices and get the report string"""
        # Mock SYMBOLDICT response
        self.mock_broker.get_symbol.return_value = "TESTSTOCK"
        self.state.client.SYMBOLDICT = {
            'NFO|12345': {
                'symbol': 'TESTSTOCK24FEB26F',
                'lp': str(ltp),
                'o': str(open_price),
                'pc': str(prev_close) if prev_close else '0'
            }
        }
        return self.summary.generate_live_scan_report(self.state)

    def test_valid_percentage(self):
        """Verify normal market moves are calculated correctly."""
        report = self._get_report_for_prices(ltp=1050, open_price=1000)
        # Expected: ((1050 - 1000) / 1000) * 100 = 5.00%
        self.assertIn("📈+5.00%", report)

    def test_garbage_open_price(self):
        """Verify that open_price = 1.0 (garbage) is caught by sanity filter."""
        report = self._get_report_for_prices(ltp=1050, open_price=1.0)
        # Expected: Sanity triggers because open < 10.0 -> Result 0.00%
        self.assertIn("📈+0.00%", report)

    def test_impossible_move(self):
        """Verify that a >20% move is caught by sanity filter."""
        report = self._get_report_for_prices(ltp=1300, open_price=1000)
        # Expected: 30% move -> caught by >20% filter -> Result 0.00%
        self.assertIn("📈+0.00%", report)

    def test_zero_open_fallback_to_prev_close(self):
        """Verify fallback to previous close if open is zero."""
        report = self._get_report_for_prices(ltp=1050, open_price=0, prev_close=1000)
        # Expected: Fallback to PC (1000) -> 5.00%
        self.assertIn("📈+5.00%", report)

if __name__ == '__main__':
    unittest.main()
