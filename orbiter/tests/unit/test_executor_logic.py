import unittest
from unittest.mock import MagicMock, patch
from orbiter.core.engine.executor import Executor
from orbiter.core.engine.state import OrbiterState
import datetime
import pytz

class TestExecutorLogic(unittest.TestCase):
    def setUp(self):
        self.mock_log_buy = MagicMock()
        self.mock_log_closed = MagicMock()
        # Mock summary_manager to avoid AttributeError
        self.mock_summary = MagicMock()
        self.executor = Executor(self.mock_log_buy, self.mock_log_closed, [], [], summary_manager=self.mock_summary)
        
        self.mock_client = MagicMock()
        self.config = {
            'TRADE_SCORE': 25.0,
            'TOP_N': 5,
            'OPTION_EXECUTE': True,
            'OPTION_PRODUCT_TYPE': 'I',
            'OPTION_PRICE_TYPE': 'LMT',
            'HEDGE_STEPS': 4,
            'OPTION_EXPIRY': 'monthly',
            'OPTION_INSTRUMENT': 'OPTSTK'
        }
        self.state = OrbiterState(self.mock_client, [], MagicMock(), self.config)

    @patch('orbiter.core.engine.executor.send_telegram_msg')
    def test_rank_signals_mcx_flow(self, mock_send):
        # 1. Setup MCX Signal (Score 50.0 > 25.0)
        scores = {'MCX|467013': 50.0}
        # Rising candles: last close is 5719, high is 5729
        mock_candles = [{'intc': str(5700 + i), 'inth': str(5710 + i), 'intl': str(5690 + i), 'stat': 'Ok'} for i in range(20)]
        self.state.client.SYMBOLDICT = {
            'MCX|467013': {
                'lp': '5729.0', # Matches Recent High
                'symbol': 'CRUDEOIL19FEB26', 'company_name': 'CRUDEOIL',
                'candles': mock_candles
            }
        }
        self.state.client.place_future_order.return_value = {'ok': True, 'tsym': 'CRUDEOIL19FEB26', 'lot_size': 100}
        self.mock_summary.get_current_funds.return_value = {'available_margin': 500000.0}
        
        # 2. Execute
        signals = self.executor.rank_signals(self.state, scores, MagicMock())

        # 3. Verify
        self.state.client.place_future_order.assert_called_once()
        self.assertIn('MCX|467013', self.state.active_positions)
        self.assertEqual(len(signals), 1)

    @patch('orbiter.core.engine.executor.send_telegram_msg')
    def test_rank_signals_nfo_flow(self, mock_send):
        # 1. Setup NFO Signal
        scores = {'NFO|12345': 45.0}
        # Rising candles: last close 2519, high 2529
        mock_candles = [{'intc': str(2500 + i), 'inth': str(2510 + i), 'intl': str(2490 + i), 'stat': 'Ok'} for i in range(20)]
        self.state.client.SYMBOLDICT = {
            'NFO|12345': {
                'lp': '2529.0', # Matches Recent High
                'symbol': 'RELIANCE24FEB26F', 'company_name': 'RELIANCE',
                'candles': mock_candles
            }
        }
        self.state.client.place_put_credit_spread.return_value = {
            'ok': True, 'expiry': '2026-02-26', 'atm_symbol': 'REL-P', 'hedge_symbol': 'REL-H', 'lot_size': 250
        }
        self.state.client.calculate_span_for_spread.return_value = {'total_margin': 150000.0}
        self.mock_summary.get_current_funds.return_value = {'available_margin': 500000.0}
        self.state.client.get_option_ltp_by_symbol.side_effect = lambda sym: 15.0 if sym == 'REL-P' else 5.0
        
        # 2. Execute
        self.executor.rank_signals(self.state, scores, MagicMock())

        # 3. Verify
        self.state.client.place_put_credit_spread.assert_called_once()
        self.assertIn('NFO|12345', self.state.active_positions)

    @patch('orbiter.core.engine.executor.send_telegram_msg')
    def test_square_off_all(self, mock_send):
        # 1. Setup Active Position
        self.state.active_positions = {
            'MCX|467013': {
                'symbol': 'CRUDEOIL', 'entry_price': 5700.0, 'strategy': 'FUTURE_LONG', 'lot_size': 100
            }
        }
        self.state.client.get_ltp.return_value = 5800.0
        self.state.client.TOKEN_TO_SYMBOL = {'467013': 'CRUDEOIL19FEB26'}

        # 2. Execute
        self.executor.square_off_all(self.state, reason="TEST EXIT")

        # 3. Verify
        self.state.client.api.place_order.assert_called_once()
        self.assertEqual(len(self.state.active_positions), 0)
        self.mock_log_closed.assert_called_once()

if __name__ == '__main__':
    unittest.main()
