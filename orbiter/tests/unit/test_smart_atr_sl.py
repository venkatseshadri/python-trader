import unittest
from orbiter.filters.sl.f1_price_increase_10 import check_sl

class TestSmartATRSL(unittest.TestCase):
    def test_future_long_hit(self):
        """Test Future Long SL hit based on ATR"""
        position = {
            'strategy': 'FUTURE_LONG',
            'entry_price': 1000.0,
            'entry_atr': 10.0,
            'atr_sl_mult': 1.5,
            'lot_size': 1,
            'stop_loss_rs': 1000
        }
        # SL should be at 1000 - (10 * 1.5) = 985.0
        
        # Test 1: No hit at 990
        data = {'lp': '990.0'}
        res = check_sl(data, position=position)
        self.assertFalse(res['hit'])
        
        # Test 2: Hit at 984
        data = {'lp': '984.0'}
        res = check_sl(data, position=position)
        self.assertTrue(res['hit'])
        self.assertIn("LTP 984.00 <= SL 985.00", res['reason'])

    def test_spread_hit(self):
        """Test Credit Spread SL hit based on ATR premium buffer"""
        position = {
            'strategy': 'PUT_CREDIT_SPREAD',
            'entry_price': 1000.0,
            'entry_net_premium': 10.0,
            'entry_atr': 10.0, # Stock ATR is 10
            'atr_sl_mult': 0.25,
            'lot_size': 100,
            'stop_loss_rs': 5000
        }
        # Premium Threshold = 10.0 + (10.0 * 0.25) = 12.50
        
        # Test 1: No hit at 12.0 premium
        data = {'current_net_premium': 12.0}
        res = check_sl(data, position=position)
        self.assertFalse(res['hit'])
        
        # Test 2: Hit at 13.0 premium
        data = {'current_net_premium': 13.0}
        res = check_sl(data, position=position)
        self.assertTrue(res['hit'])
        self.assertIn("Premium 13.00 > Threshold 12.50", res['reason'])

if __name__ == "__main__":
    unittest.main()
