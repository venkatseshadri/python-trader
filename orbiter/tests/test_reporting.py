import unittest
from unittest.mock import MagicMock
from orbiter.core.broker import BrokerClient
from orbiter.core.analytics.summary import SummaryManager

class TestMarginReporting(unittest.TestCase):
    def setUp(self):
        # 1. Mock the Shoonya API
        self.mock_api = MagicMock()
        
        # 2. Setup a BrokerClient with mocked ConnectionManager
        with unittest.mock.patch('orbiter.core.broker.ConnectionManager'):
            self.client = BrokerClient()
            # Directly set the private attribute that the property likely reads from
            # or mock the property if possible. 
            # In BrokerClient, 'self.api' is usually self.conn.api
            self.client.conn = MagicMock()
            self.client.conn.api = self.mock_api
        
        # 3. Setup SummaryManager
        self.summary = SummaryManager(self.client, 'nfo')

    def test_broker_margin_parsing(self):
        """Verify BrokerClient correctly parses raw Shoonya API response."""
        # Raw response from Shoonya get_limits()
        self.mock_api.get_limits.return_value = {
            'stat': 'Ok',
            'cash': '500000.00',
            'collateral': '250000.00',
            'marginused': '100000.00'
        }
        
        margins = self.client.get_limits()
        
        # Updated Keys Check
        self.assertEqual(margins['liquid_cash'], 500000.0)
        self.assertEqual(margins['collateral_value'], 250000.0)
        self.assertEqual(margins['total_power'], 750000.0)
        self.assertEqual(margins['margin_used'], 100000.0)

    def test_summary_report_formatting(self):
        """Verify SummaryManager correctly displays calculated margins in the message."""
        # Inject known values into mock
        self.mock_api.get_limits.return_value = {
            'stat': 'Ok',
            'cash': '100000.00',
            'collateral': '50000.00',
            'marginused': '0.00'
        }
        
        report = self.summary.generate_pre_session_report()
        
        # Check if formatted currency strings are in the report
        self.assertIn("₹100,000.00", report)
        self.assertIn("₹50,000.00", report)
        self.assertIn("₹150,000.00", report)

if __name__ == '__main__':
    unittest.main()
