import unittest
from unittest.mock import MagicMock
from orbiter.core.engine.executor import Executor
from orbiter.core.engine.state import OrbiterState

class TestGlobalTSL(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_client.SYMBOLDICT = {}
        self.mock_client.get_ltp.return_value = 100
        self.mock_filters = []
        self.mock_syncer = MagicMock()
        
        self.config = {
            'TOP_N': 5,
            'TRADE_SCORE': 0.5,
            'TOTAL_TARGET_PROFIT_RS': 1000,
            'TOTAL_STOP_LOSS_RS': 0,
            'GLOBAL_TSL_ENABLED': True,
            'GLOBAL_TSL_PCT': 20.0,
            'VERBOSE_LOGS': True,
            'OPTION_EXECUTE': False
        }
        
        # Manually create state with new attributes (since I can't easily import the *modified* class if not reloaded, but I am running tests against the *file* I just modified)
        self.state = OrbiterState(self.mock_client, [], self.mock_filters, self.config)
        self.state.active_positions = {}
        self.state.max_portfolio_pnl = 0.0
        self.state.global_tsl_active = False
        
        self.executor = Executor(MagicMock(), MagicMock(), [], [])
        self.executor.square_off_all = MagicMock(return_value=[])

    def test_global_tsl_lifecycle(self):
        # 1. Below Target -> No Activation
        self._set_pnl(500)
        self.executor.check_sl(self.state, self.mock_syncer)
        self.assertFalse(self.state.global_tsl_active)
        self.executor.square_off_all.assert_not_called()
        
        # 2. Hit Target -> Activation
        self._set_pnl(1000)
        self.executor.check_sl(self.state, self.mock_syncer)
        self.assertTrue(self.state.global_tsl_active)
        self.assertEqual(self.state.max_portfolio_pnl, 1000.0)
        self.executor.square_off_all.assert_not_called() # Should NOT exit yet, just trail
        
        # 3. Increase Profit -> Update Max
        self._set_pnl(2000)
        self.executor.check_sl(self.state, self.mock_syncer)
        self.assertEqual(self.state.max_portfolio_pnl, 2000.0)
        
        # 4. Small Retracement -> No Exit
        # Max = 2000. TSL Pct = 20%. Drop allowed = 400. Floor = 1600.
        self._set_pnl(1700)
        self.executor.check_sl(self.state, self.mock_syncer)
        self.executor.square_off_all.assert_not_called()
        
        # 5. Major Retracement -> Exit Triggered
        self._set_pnl(1500) # Below 1600
        self.executor.check_sl(self.state, self.mock_syncer)
        self.executor.square_off_all.assert_called_once()
        args, kwargs = self.executor.square_off_all.call_args
        self.assertIn("Global TSL Hit", kwargs['reason'])
        self.assertIn("Peak ₹2000.00", kwargs['reason'])
        self.assertIn("Floor ₹1600.00", kwargs['reason'])

    def _set_pnl(self, pnl_value):
        # Helper to fake portfolio PnL
        # Create a fake position that contributes exactly this PnL
        self.state.active_positions = {
            'TEST|1': {
                'entry_price': 100,
                'lot_size': 1,
                'strategy': 'FUTURE_LONG',
                'entry_time': MagicMock()
            }
        }
        # Calculate needed LTP for this PnL: PnL = (LTP - 100) * 1
        # LTP = PnL + 100
        ltp = pnl_value + 100
        self.mock_client.SYMBOLDICT['TEST|1'] = {'ltp': ltp}
        self.mock_client.get_ltp.return_value = ltp
        
        # Executor calls client.get_ltp
        self.mock_client.get_ltp = MagicMock(return_value=ltp)

if __name__ == '__main__':
    unittest.main()
