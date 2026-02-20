import unittest
from unittest.mock import MagicMock
from orbiter.core.analytics.summary import SummaryManager, TaxCalculator

class TestReportingRobustness(unittest.TestCase):
    def setUp(self):
        self.mock_broker = MagicMock()
        self.summary = SummaryManager(self.mock_broker, 'mcx', version="3.10.5")
        
        self.state = MagicMock()
        # Create a symbol with an underscore to test HTML safety
        self.state.active_positions = {
            'MCX|12345': {
                'symbol': 'SILVER_M_TEST', 
                'entry_price': 250000.0, 
                'strategy': 'FUTURE_LONG',
                'lot_size': 1
            }
        }

    def test_pnl_report_with_none_ltp(self):
        """CRITICAL: Ensure report does not crash if LTP is None"""
        self.mock_broker.get_ltp.return_value = None
        
        try:
            report = self.summary.generate_pnl_report(self.state)
            self.assertIn("SILVER_M_TEST", report)
            self.assertIn("₹0.00", report) # Should fallback to entry price
            print("✅ Verified: PnL report is resilient to None LTP.")
        except Exception as e:
            self.fail(f"PnL report crashed on None LTP: {e}")

    def test_pnl_report_html_formatting(self):
        """Ensure report uses HTML tags correctly"""
        self.mock_broker.get_ltp.return_value = 251000.0
        
        report = self.summary.generate_pnl_report(self.state)
        # Check for HTML tags instead of Markdown
        self.assertIn("<b>", report)
        self.assertIn("<code>", report)
        self.assertNotIn("`", report)
        self.assertNotIn("* ", report)
        print("✅ Verified: PnL report uses robust HTML formatting.")

    def test_tax_calculator_segment_logic(self):
        """Ensure charges are calculated differently for MCX vs NFO"""
        mcx_charges = TaxCalculator.estimate_charges(1, 1000, 'MCX')
        nfo_charges = TaxCalculator.estimate_charges(1, 1000, 'NFO')
        
        # Statutory rate for NFO (0.05%) > MCX (0.03%)
        self.assertNotEqual(mcx_charges, nfo_charges)
        print("✅ Verified: Tax Calculator is segment-aware.")

if __name__ == "__main__":
    unittest.main()
