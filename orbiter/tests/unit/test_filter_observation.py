import unittest
from orbiter.filters.sl.f1_price_increase_10 import check_sl

class TestFilterObservation(unittest.TestCase):
    def test_premium_observation_only(self):
        """Test that 10% premium rise does NOT trigger a hit (Observation Mode)"""
        position = {
            'symbol': 'LT',
            'atm_premium_entry': 10.0,
            'entry_net_premium': 9.0,
            'lot_size': 100,
            'stop_loss_rs': 5000 # Set very high so it doesn't interfere
        }
        
        # Scenario: Premium rises by 20% (Should hit observation but NOT exit)
        # Entry Net 9.0 -> Exit Net 11.0 (Rise of 2.0 = 20% of 10.0 Basis)
        current_net = 11.0
        data = {'current_net_premium': current_net}
        
        res = check_sl(position, 4000.0, data)
        self.assertFalse(res['hit'], "Filter should NOT hit in Observation Mode")
        
    def test_cash_sl_still_works(self):
        """Verify that the secondary Cash SL still functions correctly"""
        position = {
            'symbol': 'LT',
            'atm_premium_entry': 10.0,
            'entry_net_premium': 9.0,
            'lot_size': 100,
            'stop_loss_rs': 500 # ₹500 SL
        }
        
        # Scenario: Loss is ₹600 (Net rises from 9.0 to 15.0)
        current_net = 15.0
        data = {'current_net_premium': current_net}
        
        res = check_sl(position, 4000.0, data)
        self.assertTrue(res['hit'], "Secondary Cash SL should still trigger")
        self.assertIn("Total PnL", res['reason'])

if __name__ == "__main__":
    unittest.main()
