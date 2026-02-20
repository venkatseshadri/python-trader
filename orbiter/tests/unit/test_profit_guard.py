import unittest
from orbiter.filters.tp.f2_trailing_sl import check_trailing_sl

class TestProfitGuardPro(unittest.TestCase):
    def test_tight_trailing_hit(self):
        """Test the 'BAJFINANCE scenario': 5.64% peak should exit early with 0.75% gap"""
        position = {
            'symbol': 'BAJFINANCE',
            'atm_premium_entry': 10.0,
            'entry_net_premium': 9.0,
            'max_profit_pct': 5.64, # Peak reached
            'tp_trail_activation': 1.5,
            'tp_trail_gap': 0.75
        }
        
        # Scenario: Profit drops to 4.80% (Gap is 0.75%, so threshold is 5.64 - 0.75 = 4.89%)
        # At 4.80% profit, it should be a HIT.
        current_net = 8.52 # (9.0 - 8.52) / 10.0 * 100 = 4.80%
        data = {'current_net_premium': current_net}
        
        res = check_trailing_sl(position, 1000.0, data)
        self.assertTrue(res['hit'])
        self.assertIn("Profit Guard Pro hit", res['reason'])
        self.assertIn("Trail-Floor 4.89", res['reason'])

    def test_peak_lock_mechanism(self):
        """Test that if profit > 3%, SL never falls below 1.0% (guaranteed green)"""
        position = {
            'symbol': 'TEST',
            'atm_premium_entry': 10.0,
            'entry_net_premium': 9.0,
            'max_profit_pct': 3.1, # Crossed the 3% peak-lock threshold
            'tp_trail_activation': 1.5,
            'tp_trail_gap': 5.0 # Even if gap is huge (dumb legacy value)
        }
        
        # 3.1 - 5.0 = -1.9 (Red), but Peak-Lock should force it to +1.0% (Green)
        # Current profit drops to 0.5% (Should be hit because floor is 1.0%)
        current_net = 8.95 # (9.0 - 8.95) / 10.0 * 100 = 0.5%
        data = {'current_net_premium': current_net}
        
        res = check_trailing_sl(position, 1000.0, data)
        self.assertTrue(res['hit'])
        self.assertIn("Trail-Floor 1.00", res['reason'])

if __name__ == "__main__":
    unittest.main()
