import unittest
from unittest.mock import MagicMock, patch
from orbiter.core.engine.executor import Executor
from orbiter.core.engine.state import OrbiterState
import datetime
import pytz

class TestEngineExecutorCore(unittest.TestCase):

    def setUp(self):
        self.mock_log_buy = MagicMock()
        self.mock_log_closed = MagicMock()
        self.executor = Executor(self.mock_log_buy, self.mock_log_closed, [], [])
        
        self.mock_client = MagicMock()
        self.mock_client.SYMBOLDICT = {}
        self.state = OrbiterState(self.mock_client, [], [], {'TOP_N': 5, 'TRADE_SCORE': 0.5})

    def test_square_off_all_futures(self):
        """Verify mass square off for future positions"""
        token = "MCX|467013"
        self.state.active_positions[token] = {
            'symbol': 'CRUDEOIL', 'entry_price': 5700.0, 'lot_size': 100, 
            'strategy': 'FUTURE_LONG', 'entry_time': datetime.datetime.now()
        }
        self.mock_client.get_ltp.return_value = 5750.0
        
        with patch('orbiter.core.engine.executor.send_telegram_msg') as mock_send:
            res = self.executor.square_off_all(self.state, reason="Test Exit")
            
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]['pct_change'], 0.8771929824561403)
            self.assertEqual(len(self.state.active_positions), 0) # Should be cleared
            mock_send.assert_called_once()
            self.assertIn("Mass Square Off Complete", mock_send.call_args[0][0])

    def test_check_sl_logic_trigger(self):
        """Verify SL filter trigger and position removal"""
        token = "NFO|12345"
        self.state.active_positions[token] = {
            'symbol': 'TEST', 'entry_price': 100.0, 'lot_size': 1, 
            'strategy': 'FUTURE_LONG', 'entry_time': datetime.datetime.now()
        }
        self.mock_client.SYMBOLDICT[token] = {'ltp': 95.0}
        
        # Add a mock SL filter that triggers
        mock_filter = MagicMock()
        mock_filter.evaluate.return_value = {'hit': True, 'reason': 'Price Drop', 'pct': -5.0}
        self.executor.sl_filters = [mock_filter]
        
        mock_syncer = MagicMock()
        
        res = self.executor.check_sl(self.state, mock_syncer)
        
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]['reason'], 'Price Drop')
        self.assertNotIn(token, self.state.active_positions) # Should be removed

if __name__ == '__main__':
    unittest.main()
