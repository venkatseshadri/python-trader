import unittest
from unittest.mock import MagicMock
from orbiter.core.engine.action.executors.options import OptionActionExecutor


class TestOptionActionExecutor(unittest.TestCase):
    def setUp(self):
        self.state = MagicMock()
        self.state.client.segment_name = "nfo"
        self.state.client.get_token.return_value = "26000"
        self.state.client.get_ltp.return_value = 25000.0
        self.state.client.resolver.resolve_option_symbol.return_value = {
            "ok": True,
            "tradingsymbol": "NIFTY26FEB25000CE",
            "exchange": "NFO",
            "lot_size": 50,
        }
        self.state.client.api.place_order = MagicMock(return_value={"stat": "Ok"})
        self.executor = OptionActionExecutor(self.state)

    def test_exec_builds_order(self):
        res = self.executor.execute(symbol="NIFTY", option="CE", strike="ATM", qty_multiplier=2)
        self.state.client.resolver.resolve_option_symbol.assert_called_once()
        self.state.client.api.place_order.assert_called_once()
        args, kwargs = self.state.client.api.place_order.call_args
        self.assertEqual(kwargs["tradingsymbol"], "NIFTY26FEB25000CE")
        self.assertEqual(kwargs["quantity"], 100)
        self.assertEqual(res["stat"], "Ok")


if __name__ == "__main__":
    unittest.main()
