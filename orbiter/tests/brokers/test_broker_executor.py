import unittest
from unittest.mock import MagicMock
from orbiter.core.broker.executor import OrderExecutor

class TestOrderExecutor(unittest.TestCase):

    def setUp(self):
        self.mock_api = MagicMock()
        self.mock_logger = MagicMock()
        self.executor = OrderExecutor(self.mock_api, self.mock_logger)

    def test_place_future_order_simulation(self):
        """Verify simulation mode returns ok:True and dry_run:True"""
        details = {'tsym': 'CRUDEOIL-FUT', 'lot_size': 100, 'exchange': 'MCX', 'token': '467013'}
        res = self.executor.place_future_order(details, 'B', execute=False, product_type='I', price_type='MKT')
        
        self.assertTrue(res['ok'])
        self.assertTrue(res['dry_run'])
        self.assertEqual(res['tsym'], 'CRUDEOIL-FUT')
        # Ensure no API call was made
        self.mock_api.place_order.assert_not_called()

    def test_place_future_order_live_success(self):
        """Verify successful live future order"""
        details = {'tsym': 'SBIN-FUT', 'lot_size': 1500, 'exchange': 'NFO', 'token': '1234'}
        self.mock_api.place_order.return_value = {'stat': 'Ok', 'norenordno': 'OR123'}
        
        res = self.executor.place_future_order(details, 'B', execute=True, product_type='I', price_type='MKT')
        
        self.assertTrue(res['ok'])
        self.assertEqual(res['resp']['norenordno'], 'OR123')
        self.mock_api.place_order.assert_called_once()

    def test_place_spread_simulation(self):
        """Verify spread simulation mode"""
        spread = {
            'atm_symbol': 'SBIN-P600', 'hedge_symbol': 'SBIN-P580', 
            'lot_size': 1500, 'side': 'PUT', 'exchange': 'NFO'
        }
        res = self.executor.place_spread(spread, execute=False, product_type='I', price_type='MKT')
        
        self.assertTrue(res['dry_run'])
        self.assertEqual(res['atm_symbol'], 'SBIN-P600')
        self.mock_api.place_order.assert_not_called()

    def test_place_spread_live_failure_hedge(self):
        """Verify failure when hedge leg fails (should not place ATM)"""
        spread = {
            'atm_symbol': 'SBIN-P600', 'hedge_symbol': 'SBIN-P580', 
            'lot_size': 1500, 'side': 'PUT', 'exchange': 'NFO'
        }
        # Hedge leg fails
        self.mock_api.place_order.return_value = {'stat': 'Not_Ok', 'emsg': 'Insufficient Margin'}
        
        res = self.executor.place_spread(spread, execute=True, product_type='I', price_type='MKT')
        
        self.assertFalse(res['ok'])
        self.assertIn('hedge_leg_failed', res['reason'])
        # Only one call (for hedge)
        self.assertEqual(self.mock_api.place_order.call_count, 1)

if __name__ == '__main__':
    unittest.main()
