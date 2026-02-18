import unittest
from unittest.mock import MagicMock, patch
from core.broker import BrokerClient
from core.analytics.summary import SummaryManager

class TestMarginReporting(unittest.TestCase):
    def setUp(self):
        # Mock the API Connection
        self.mock_api = MagicMock()
        
        # Initialize BrokerClient with a mocked API
        with patch('core.broker.ConnectionManager') as mock_conn:
            mock_conn.return_value.api = self.mock_api
            self.client = BrokerClient(segment_name='nfo')
            self.client.conn.api = self.mock_api # Force injection
            
        self.summary = SummaryManager(self.client, 'nfo')

    def test_broker_margin_parsing(self):
        """Verify BrokerClient correctly parses raw Shoonya API response."""
        # 1. Mock Raw Shoonya Response for get_limits()
        self.mock_api.get_limits.return_value = {
            'stat': 'Ok',
            'cash': '500000.00',      # Total Limit
            'marginused': '150000.00' # Utilized Margin
        }
        
        # 2. Call the method
        margins = self.client.get_limits()
        
        # 3. Assertions
        self.assertEqual(margins['cash'], 500000.0)
        self.assertEqual(margins['margin_used'], 150000.0)
        self.assertEqual(margins['available'], 350000.0) # 500k - 150k

    def test_summary_report_formatting(self):
        """Verify SummaryManager correctly displays calculated margins in the message."""
        # 1. Mock the client methods used by the report
        self.client.get_limits = MagicMock(return_value={
            'cash': 1000000.0,
            'margin_used': 200000.0,
            'available': 800000.0
        })
        self.client.get_positions = MagicMock(return_value=[])
        
        # 2. Generate Report
        report = self.summary.generate_pre_session_report()
        
        # 3. Assertions: Check if the strings appear correctly formatted (including Markdown)
        self.assertIn("*Available Margin:* ₹800,000.00", report)
        self.assertIn("*Margin Used:* ₹200,000.00", report)
        self.assertIn("*Cash Balance:* ₹1,000,000.00", report)

    def test_pnl_net_calculation(self):
        """Verify the TaxCalculator correctly handles brokerage and statutory charges."""
        from core.analytics.summary import TaxCalculator
        
        # Scenario: 4 Executed orders (8 legs total), ₹10,000 Gross PnL
        num_orders = 4 
        gross_pnl = 10000.0
        segment = 'NFO'
        
        # Expected: (4 * 20.0) + (10000 * 0.0005) = 80 + 5 = ₹85
        charges = TaxCalculator.estimate_charges(num_orders, gross_pnl, segment)
        self.assertEqual(charges, 85.0)

if __name__ == '__main__':
    unittest.main()
