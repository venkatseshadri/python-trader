import unittest
from types import SimpleNamespace

from orbiter.core.broker.margin import MarginCalculator


class FakeApi:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def span_calculator(self, actid, positionlist):
        self.calls.append((actid, positionlist))
        return self.response


class FakeMaster:
    def __init__(self, rows):
        self.DERIVATIVE_OPTIONS = rows


class TestMarginCalculator(unittest.TestCase):
    def test_calculate_span_for_spread_ok(self):
        rows = [
            {
                'tradingsymbol': 'ATM',
                'symbol': 'RECLTD',
                'instrument': 'OPTSTK',
                'exchange': 'NFO',
                'expiry': '2026-03-26',
                'option_type': 'CE',
                'strike': '500',
                'lotsize': '25'
            },
            {
                'tradingsymbol': 'HEDGE',
                'symbol': 'RECLTD',
                'instrument': 'OPTSTK',
                'exchange': 'NFO',
                'expiry': '2026-03-26',
                'option_type': 'PE',
                'strike': '450',
                'lotsize': '25'
            }
        ]
        master = FakeMaster(rows)
        api = FakeApi({'stat': 'Ok', 'span': '1000', 'expo': '200'})
        calc = MarginCalculator(master)

        spread = {
            'atm_symbol': 'ATM',
            'hedge_symbol': 'HEDGE',
            'lot_size': 25
        }
        res = calc.calculate_span_for_spread(spread, api, 'ACCT')

        self.assertTrue(res['ok'])
        self.assertEqual(res['span'], 1000.0)
        self.assertEqual(res['expo'], 200.0)
        self.assertEqual(res['total_margin'], 1200.0)
        self.assertIn('pledged_required', res)
        self.assertEqual(len(api.calls), 1)

    def test_calculate_span_for_spread_span_zero(self):
        rows = [
            {
                'tradingsymbol': 'ATM',
                'symbol': 'RECLTD',
                'instrument': 'OPTSTK',
                'exchange': 'NFO',
                'expiry': '2026-03-26',
                'option_type': 'CE',
                'strike': '500',
                'lotsize': '25'
            },
            {
                'tradingsymbol': 'HEDGE',
                'symbol': 'RECLTD',
                'instrument': 'OPTSTK',
                'exchange': 'NFO',
                'expiry': '2026-03-26',
                'option_type': 'PE',
                'strike': '450',
                'lotsize': '25'
            }
        ]
        master = FakeMaster(rows)
        api = FakeApi({'stat': 'Ok', 'span': '0', 'expo': '0'})
        calc = MarginCalculator(master)

        res = calc.calculate_span_for_spread({'atm_symbol': 'ATM', 'hedge_symbol': 'HEDGE', 'lot_size': 25}, api, 'ACCT')
        self.assertFalse(res['ok'])
        self.assertEqual(res['reason'], 'span_zero')

    def test_calculate_future_margin_ok(self):
        rows = [
            {
                'tradingsymbol': 'RECLTDFUT',
                'symbol': 'RECLTD',
                'instrument': 'FUTSTK',
                'exchange': 'NFO',
                'expiry': '2026-03-26',
                'option_type': 'XX',
                'strike': '0',
                'lotsize': '25'
            }
        ]
        master = FakeMaster(rows)
        api = FakeApi({'stat': 'Ok', 'span': '1500', 'expo': '100'})
        calc = MarginCalculator(master)

        res = calc.calculate_future_margin({'tsym': 'RECLTDFUT', 'lot_size': 25}, api, 'ACCT')
        self.assertTrue(res['ok'])
        self.assertEqual(res['total_margin'], 1600.0)


if __name__ == '__main__':
    unittest.main()
