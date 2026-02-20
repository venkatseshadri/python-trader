import unittest
from unittest.mock import MagicMock, patch
from orbiter.core.analytics.summary import SummaryManager, TaxCalculator
from orbiter.core.engine.syncer import Syncer
from orbiter.core.engine.state import OrbiterState
import datetime

class TestAnalyticsAndSync(unittest.TestCase):

    def setUp(self):
        self.mock_broker = MagicMock()
        self.summary = SummaryManager(self.mock_broker, 'nfo', version="3.9.6")

    def test_tax_calculator(self):
        """Verify statutory charge estimations"""
        # NFO: 2 orders, 1000 PnL
        charges = TaxCalculator.estimate_charges(2, 1000.0, 'NFO')
        # 2*20 + 1000*0.0005 = 40 + 0.5 = 40.5
        self.assertEqual(charges, 40.5)

    def test_pre_session_report(self):
        """Verify pre-market report formatting"""
        self.mock_broker.get_limits.return_value = {
            'total_power': 100000.0, 'margin_used': 20000.0, 
            'available': 80000.0, 'collateral_value': 50000.0, 'liquid_cash': 50000.0
        }
        self.mock_broker.get_positions.return_value = []
        
        report = self.summary.generate_pre_session_report()
        self.assertIn("NFO SESSION PREP", report)
        self.assertIn("₹80,000.00", report)

    def test_margin_status_report(self):
        """Verify concise margin report"""
        self.mock_broker.get_limits.return_value = {
            'available': 80000.0, 'margin_used': 20000.0, 
            'collateral_value': 50000.0, 'liquid_cash': 50000.0
        }
        report = self.summary.generate_margin_status()
        self.assertIn("Margin Update (NFO)", report)
        self.assertIn("Available:* ₹80,000.00", report)

    def test_syncer_logic(self):
        """Verify active position payload construction for Sheets"""
        mock_update_func = MagicMock()
        syncer = Syncer(mock_update_func)
        
        # Setup state with one position
        state = MagicMock() # Don't use spec=OrbiterState to allow easy attribute setting
        state.verbose_logs = False
        token = "NFO|59391"
        state.active_positions = {
            token: {
                'symbol': 'JSWSTEEL', 'company_name': 'JSWSTEEL', 
                'entry_price': 1200.0, 'lot_size': 700, 
                'strategy': 'FUTURE_LONG', 'entry_time': datetime.datetime.now(),
                'max_profit_pct': 1.0, 'max_pnl_rs': 1000.0
            }
        }
        
        # Initialize nested client mock
        state.client = MagicMock()
        state.client.SYMBOLDICT = {token: {'ltp': 1210.0}}
        state.client.span_cache = {}
        state.config = {}
        
        syncer.sync_active_positions_to_sheets(state)
        
        # Verify update function was called with correct payload
        mock_update_func.assert_called_once()
        payload = mock_update_func.call_args[0][0]
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['symbol'], 'JSWSTEEL')
        self.assertEqual(payload[0]['ltp'], 1210.0)

    def test_live_scan_report(self):
        """Verify live status report with scores and positions"""
        state = MagicMock()
        token = "NFO|59391"
        state.symbols = [token]
        state.filter_results_cache = {
            token: {'ef1_orb': {'score': 1.16}}
        }
        state.active_positions = {
            token: {
                'symbol': 'JSWSTEEL', 'entry_price': 1200.0, 'lot_size': 700, 
                'strategy': 'FUTURE_LONG'
            }
        }
        state.config = {'SIMULATION': True}
        state.client.SYMBOLDICT = {token: {'lp': 1210.0, 'symbol': 'JSWSTEEL'}}
        state.client.get_ltp.return_value = 1210.0
        
        report = self.summary.generate_live_scan_report(state)
        self.assertIn("[SIMULATION]", report)
        self.assertIn("JSWSTEEL", report)
        self.assertIn("1.16", report)
        self.assertIn("₹7,000.00", report) # (1210-1200) * 700

if __name__ == '__main__':
    unittest.main()
