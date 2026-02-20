import unittest
from unittest.mock import MagicMock
from orbiter.core.broker.margin import MarginCalculator

class TestMarginCalculator(unittest.TestCase):

    def setUp(self):
        self.mock_master = MagicMock()
        # Mock DERIVATIVE_OPTIONS with some sample rows
        self.mock_master.DERIVATIVE_OPTIONS = [
            {
                'tradingsymbol': 'SBIN24FEB26P600',
                'symbol': 'SBIN',
                'expiry': '2026-02-24',
                'option_type': 'PE',
                'strike': 600.0,
                'instrument': 'OPTSTK'
            },
            {
                'tradingsymbol': 'SBIN24FEB26P580',
                'symbol': 'SBIN',
                'expiry': '2026-02-24',
                'option_type': 'PE',
                'strike': 580.0,
                'instrument': 'OPTSTK'
            },
            {
                'tradingsymbol': 'CRUDEOIL19FEB26F',
                'symbol': 'CRUDEOIL',
                'expiry': '2026-02-19',
                'instrument': 'FUTCOM'
            }
        ]
        self.calculator = MarginCalculator(self.mock_master)
        self.mock_api = MagicMock()

    def test_calculate_span_for_spread_success(self):
        """Verify successful spread margin calculation"""
        spread = {
            'atm_symbol': 'SBIN24FEB26P600',
            'hedge_symbol': 'SBIN24FEB26P580',
            'lot_size': 1500
        }
        
        self.mock_api.span_calculator.return_value = {
            'stat': 'Ok',
            'span': '50000.0',
            'expo': '10000.0',
            'span_trade': '50000',
            'expo_trade': '10000',
            'pre_trade': '60000'
        }
        
        res = self.calculator.calculate_span_for_spread(spread, self.mock_api, 'ACT123')
        
        self.assertTrue(res['ok'])
        self.assertEqual(res['span'], 50000.0)
        self.assertEqual(res['total_margin'], 60000.0)
        self.assertAlmostEqual(res['pledged_required'], 75000.0) # 60000 / 0.8

    def test_calculate_span_for_spread_missing_symbol(self):
        """Verify handling of missing symbols in master"""
        spread = {'atm_symbol': 'MISSING', 'hedge_symbol': 'SBIN24FEB26P580'}
        res = self.calculator.calculate_span_for_spread(spread, self.mock_api, 'ACT123')
        self.assertFalse(res['ok'])
        self.assertEqual(res['reason'], 'option_symbol_not_found')

    def test_calculate_span_for_spread_api_error(self):
        """Verify handling of API error response"""
        spread = {
            'atm_symbol': 'SBIN24FEB26P600',
            'hedge_symbol': 'SBIN24FEB26P580',
            'lot_size': 1500
        }
        self.mock_api.span_calculator.return_value = {'stat': 'Not_Ok', 'emsg': 'Invalid Token'}
        
        res = self.calculator.calculate_span_for_spread(spread, self.mock_api, 'ACT123')
        self.assertFalse(res['ok'])
        self.assertIn('span_err', res['reason'])

    def test_calculate_future_margin_mcx(self):
        """Verify successful MCX future margin calculation"""
        details = {
            'tsym': 'CRUDEOIL19FEB26F',
            'lot_size': 100
        }
        self.mock_api.span_calculator.return_value = {
            'stat': 'Ok',
            'span': '150000.0',
            'expo': '30000.0'
        }
        
        res = self.calculator.calculate_future_margin(details, self.mock_api, 'ACT123')
        
        self.assertTrue(res['ok'])
        self.assertEqual(res['total_margin'], 180000.0)
        # Verify exch was MCX in the call
        args, kwargs = self.mock_api.span_calculator.call_args
        self.assertEqual(args[1][0]['exch'], 'MCX')

if __name__ == '__main__':
    unittest.main()
