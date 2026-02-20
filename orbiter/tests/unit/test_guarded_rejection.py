import unittest
from unittest.mock import MagicMock, patch
from orbiter.core.engine.executor import Executor
from orbiter.core.engine.state import OrbiterState
import numpy as np

class TestGuardedRejection(unittest.TestCase):
    def setUp(self):
        self.mock_summary = MagicMock()
        self.executor = Executor(MagicMock(), MagicMock(), [], [], summary_manager=self.mock_summary)
        self.mock_client = MagicMock()
        self.config = {'TRADE_SCORE': 25.0, 'TOP_N': 5}
        self.state = OrbiterState(self.mock_client, [], MagicMock(), self.config)

    @patch('orbiter.core.engine.executor.send_telegram_msg')
    def test_rejection_on_negative_slope(self, mock_send):
        """
        SCENARIO: SILVER has a huge score (50.0), but the price is falling.
        The Slope Guard (EMA5) should block the entry.
        """
        # 1. Setup High-Score Signal
        scores = {'MCX|SILVER': 50.0}
        
        # 2. Create FALLING candles (Slope Negative)
        mock_candles = [{'intc': str(250000 - i), 'inth': str(250100 - i), 'intl': str(249900 - i), 'stat': 'Ok'} for i in range(20)]
        
        self.state.client.SYMBOLDICT = {
            'MCX|SILVER': {
                'lp': '249980.0', 
                'symbol': 'SILVER05MAR26', 'company_name': 'SILVER',
                'candles': mock_candles
            }
        }
        
        # 3. Execute Ranking
        signals = self.executor.rank_signals(self.state, scores, MagicMock())

        # 4. VERIFY: No trade was taken despite the high score
        self.assertEqual(len(signals), 0, "Bot incorrectly traded on a negative slope!")
        self.state.client.place_future_order.assert_not_called()

    @patch('orbiter.core.engine.executor.send_telegram_msg')
    def test_rejection_on_stale_price(self, mock_send):
        """
        SCENARIO: Score is high, but price is 1% below the 15-minute high.
        The Freshness Guard should block it.
        """
        scores = {'MCX|SILVER': 50.0}
        
        # Create candles where high was 250,000 but current price is 247,000 (1% drop)
        mock_candles = [{'intc': '250000', 'inth': '250000', 'intl': '249000', 'stat': 'Ok'} for i in range(20)]
        
        self.state.client.SYMBOLDICT = {
            'MCX|SILVER': {
                'lp': '247000.0', # 1.2% below high
                'symbol': 'SILVER05MAR26', 'company_name': 'SILVER',
                'candles': mock_candles
            }
        }
        
        signals = self.executor.rank_signals(self.state, scores, MagicMock())

        self.assertEqual(len(signals), 0, "Bot incorrectly traded on a stale price!")

if __name__ == "__main__":
    unittest.main()
