import unittest
from unittest.mock import MagicMock, patch
from orbiter.core.broker.connection import ConnectionManager
from orbiter.core.analytics.summary import SummaryManager
import yaml
import os

class TestConnectionAndDebrief(unittest.TestCase):

    @patch('orbiter.core.broker.connection.ShoonyaApiPy')
    @patch('yaml.load')
    @patch('builtins.open', unittest.mock.mock_open())
    def test_login_success(self, mock_yaml, mock_api_class):
        """Verify successful login path"""
        mock_yaml.return_value = {
            'user': 'FA333160', 'pwd': 'dummy', 'factor2': '123456',
            'vc': 'V123', 'apikey': 'key', 'imei': 'abc'
        }
        
        mock_api = mock_api_class.return_value
        mock_api.login.return_value = {'stat': 'Ok'}
        
        conn = ConnectionManager(config_path='fake.yml')
        res = conn.login(factor2_override="111111")
        self.assertTrue(res)
        self.assertEqual(conn.cred['factor2'], "111111")

    def test_post_session_report(self):
        """Verify post-session debrief report generation"""
        mock_broker = MagicMock()
        summary = SummaryManager(mock_broker, 'nfo')
        
        # Mock broker data
        mock_broker.get_limits.return_value = {'available': 105000.0}
        mock_broker.get_order_history.return_value = [
            {'status': 'COMPLETE'}, {'status': 'CANCELED'}
        ]
        mock_broker.get_positions.return_value = [
            {'tsym': 'SBIN', 'netqty': '0', 'rpnl': '1000.0', 'urpnl': '0.0'}
        ]
        
        report = summary.generate_post_session_report()
        self.assertIn("NFO SESSION DEBRIEF", report)
        self.assertIn("Gross PnL:</b> ₹1,000.00", report)
        self.assertIn("Net PnL (Est):</b> ₹979.50", report) # 1000 - (1*20 + 1000*0.0005) = 1000 - 20.5 = 979.5

if __name__ == '__main__':
    unittest.main()
