import unittest
from orbiter.filters.tp.f2_trailing_sl import check_trailing_sl

class TestProfitGuardPro(unittest.TestCase):
    def test_cash_trailing_hit(self):
        """Test the 'Smart SL scenario': Peak ₹2000, 40% retracement means exit at ₹1200"""
        position = {
            'symbol': 'TEST',
            'max_pnl_rs': 2000.0,
            'pnl_rs': 1100.0, # Below the ₹1200 floor
            'tsl_retracement_pct': 40,
            'tsl_activation_rs': 1000
        }
        
        res = check_trailing_sl({}, position=position)
        self.assertTrue(res['hit'])
        self.assertIn("Cash TSL Hit", res['reason'])
        self.assertIn("Floor ₹1200", res['reason'])

    def test_cash_peak_lock_mechanism(self):
        """Test that if Peak PnL > ₹2000, SL never falls below ₹500 (guaranteed green)"""
        position = {
            'symbol': 'TEST',
            'max_pnl_rs': 2500.0,
            'pnl_rs': 400.0, # Below the ₹500 floor-lock
            'tsl_retracement_pct': 90, # Huge gap would normally mean exit at ₹250
            'tsl_activation_rs': 1000
        }
        
        # 90% of 2500 is 2250 drop. 2500 - 2250 = ₹250 floor.
        # But Peak-Lock forces floor to ₹500.
        res = check_trailing_sl({}, position=position)
        self.assertTrue(res['hit'])
        self.assertIn("Floor ₹500", res['reason'])

if __name__ == "__main__":
    unittest.main()
