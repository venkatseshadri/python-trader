import unittest
from unittest.mock import MagicMock
from orbiter.core.engine.action.executor import ActionExecutor


class TestEngineExecutorCore(unittest.TestCase):
    def setUp(self):
        self.state = MagicMock()
        self.executor = ActionExecutor(self.state)

    def test_route_option_order(self):
        self.executor._option_live.execute = MagicMock(return_value={"ok": True})
        self.executor._future_live.execute = MagicMock()
        self.executor._equity_live.execute = MagicMock()

        res = self.executor.place_order(option="CE", strike="ATM", symbol="NIFTY")

        self.executor._option_live.execute.assert_called_once()
        self.executor._future_live.execute.assert_not_called()
        self.executor._equity_live.execute.assert_not_called()
        self.assertEqual(res, {"ok": True})

    def test_route_future_order(self):
        self.executor._future_live.execute = MagicMock(return_value={"ok": True})
        self.executor._option_live.execute = MagicMock()
        self.executor._equity_live.execute = MagicMock()

        res = self.executor.place_order(derivative="future", symbol="RELIANCEFUT")

        self.executor._future_live.execute.assert_called_once()
        self.executor._option_live.execute.assert_not_called()
        self.executor._equity_live.execute.assert_not_called()
        self.assertEqual(res, {"ok": True})

    def test_route_equity_order(self):
        self.executor._equity_live.execute = MagicMock(return_value={"ok": True})
        self.executor._option_live.execute = MagicMock()
        self.executor._future_live.execute = MagicMock()

        res = self.executor.place_order(symbol="RELIANCE")

        self.executor._equity_live.execute.assert_called_once()
        self.executor._option_live.execute.assert_not_called()
        self.executor._future_live.execute.assert_not_called()
        self.assertEqual(res, {"ok": True})


if __name__ == '__main__':
    unittest.main()
