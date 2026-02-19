import unittest
from unittest.mock import MagicMock, patch
from orbiter.core.engine.evaluator import Evaluator
from orbiter.core.engine.state import OrbiterState
import datetime
import pytz

class TestEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = Evaluator()
        self.mock_client = MagicMock()
        self.config = {
            'SIMULATION': True,
            'TRADE_SCORE': 25.0,
            'TOP_N': 5,
            'OPTION_EXPIRY': 'monthly',
            'OPTION_INSTRUMENT': 'OPTSTK',
            'HEDGE_STEPS': 4,
            'OPTION_PRODUCT_TYPE': 'I'
        }
        # Mocking the filters module
        self.mock_filters_module = MagicMock()
        self.state = OrbiterState(self.mock_client, ['NFO|12345'], self.mock_filters_module, self.config)

    @patch('orbiter.core.engine.evaluator.datetime')
    @patch('orbiter.core.engine.evaluator.get_today_orb_times')
    def test_evaluate_filters_basic_flow(self, mock_orb_times, mock_datetime):
        # 1. Setup Mock Times (10:00 AM IST)
        tz = pytz.timezone('Asia/Kolkata')
        frozen_now = datetime.datetime(2026, 2, 18, 10, 0, tzinfo=tz)
        mock_datetime.now.return_value = frozen_now
        # Ensure we don't break other datetime calls
        mock_datetime.fromtimestamp = datetime.datetime.fromtimestamp
        
        mock_orb_times.return_value = (frozen_now.replace(hour=9, minute=15), frozen_now.replace(hour=15, minute=30))

        # 2. Mock API Responses
        self.mock_client.api.get_time_price_series.return_value = [
            {'stat': 'Ok', 'time': '09:15', 'into': '100.0', 'inth': '105.0', 'intl': '99.0', 'intc': '101.0'},
            {'stat': 'Ok', 'time': '09:16', 'into': '101.0', 'inth': '102.0', 'intl': '100.0', 'intc': '101.5'},
            {'stat': 'Ok', 'time': '09:17', 'into': '101.0', 'inth': '102.0', 'intl': '100.0', 'intc': '101.5'},
            {'stat': 'Ok', 'time': '09:18', 'into': '101.0', 'inth': '102.0', 'intl': '100.0', 'intc': '101.5'},
            {'stat': 'Ok', 'time': '09:19', 'into': '101.0', 'inth': '102.0', 'intl': '100.0', 'intc': '101.5'}
        ]
        self.mock_client.SYMBOLDICT = {
            'NFO|12345': {'lp': '102.0', 'o': '100.0', 'h': '105.0', 'l': '99.0', 'c': '98.0'}
        }
        self.mock_client.get_symbol.return_value = "TESTSTOCK"
        self.mock_client.get_company_name.return_value = "TEST COMPANY"
        
        # Mock filters within the module
        mock_f1 = MagicMock()
        mock_f1.key = 'f1_orb' # Matching the weight index 0
        mock_f1.evaluate.return_value = {'score': 10.0, 'orb_high': 105.0}
        
        self.mock_filters_module.get_filters.return_value = [mock_f1]

        # 3. Execute
        score = self.evaluator.evaluate_filters(self.state, 'NFO|12345')

        # 4. Verify
        # Since we set ENTRY_WEIGHTS in config, default time-based weights are bypassed
        # Weight for index 0 is 1.0. Score 10.0 * 1.0 = 10.0
        self.assertEqual(score, 10.0)

    def test_candle_stats_calculation(self):
        """Verify _candle_stats correctly parses OHLC from series"""
        candles = [
            {'stat': 'Ok', 'tm': '09:15', 'into': '100', 'inth': '110', 'intl': '90', 'intc': '105'},
            {'stat': 'Ok', 'tm': '09:16', 'into': '105', 'inth': '115', 'intl': '100', 'intc': '112'}
        ]
        o, h, l, c = self.evaluator._candle_stats(candles, self.evaluator._time_key)
        self.assertEqual(o, 100.0)
        self.assertEqual(h, 115.0)
        self.assertEqual(l, 90.0)
        self.assertEqual(c, 112.0)

if __name__ == '__main__':
    unittest.main()
