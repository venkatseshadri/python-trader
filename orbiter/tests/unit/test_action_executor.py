import unittest
from unittest.mock import MagicMock
from orbiter.core.engine.action.executor import ActionExecutor


class TestActionExecutorRouting(unittest.TestCase):
    def setUp(self):
        self.state = MagicMock()
        self.executor = ActionExecutor(self.state)
        # Stub workers
        self.executor._option_live.execute = MagicMock(return_value={"ok": True, "type": "option"})
        self.executor._future_live.execute = MagicMock(return_value={"ok": True, "type": "future"})
        self.executor._equity_live.execute = MagicMock(return_value={"ok": True, "type": "equity"})

    def test_route_option(self):
        res = self.executor.place_order(option="CE", strike="ATM", symbol="NIFTY")
        self.executor._option_live.execute.assert_called_once()
        self.executor._future_live.execute.assert_not_called()
        self.executor._equity_live.execute.assert_not_called()
        self.assertEqual(res["type"], "option")

    def test_route_future(self):
        res = self.executor.place_order(derivative="future", symbol="RELIANCEFUT")
        self.executor._future_live.execute.assert_called_once()
        self.executor._option_live.execute.assert_not_called()
        self.executor._equity_live.execute.assert_not_called()
        self.assertEqual(res["type"], "future")

    def test_route_equity(self):
        res = self.executor.place_order(symbol="RELIANCE")
        self.executor._equity_live.execute.assert_called_once()
        self.executor._option_live.execute.assert_not_called()
        self.executor._future_live.execute.assert_not_called()
        self.assertEqual(res["type"], "equity")


if __name__ == "__main__":
    unittest.main()
