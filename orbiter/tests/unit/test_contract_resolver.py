import unittest
import datetime

from orbiter.core.broker.resolver import ContractResolver


class FakeMaster:
    def __init__(self, rows):
        self.DERIVATIVE_OPTIONS = rows
        self.DERIVATIVE_LOADED = True
        self._last_refresh_time = 0

    def download_scrip_master(self, exchange):
        self.DERIVATIVE_LOADED = True

    def _parse_expiry_date(self, raw):
        try:
            return datetime.datetime.strptime(raw, "%Y-%m-%d").date()
        except Exception:
            return None


class TestContractResolver(unittest.TestCase):
    def _make_rows(self):
        return [
            {
                'symbol': 'RECLTD',
                'instrument': 'OPTSTK',
                'exchange': 'NFO',
                'expiry': '2026-03-05',
                'strike': '500',
                'option_type': 'CE',
                'tradingsymbol': 'RECLTD26MAR500CE',
                'token': '111',
                'lotsize': '25'
            },
            {
                'symbol': 'RECLTD',
                'instrument': 'OPTSTK',
                'exchange': 'NFO',
                'expiry': '2026-03-12',
                'strike': '510',
                'option_type': 'CE',
                'tradingsymbol': 'RECLTD26MAR510CE',
                'token': '112',
                'lotsize': '25'
            },
            {
                'symbol': 'RECLTD',
                'instrument': 'OPTSTK',
                'exchange': 'NFO',
                'expiry': '2026-03-26',
                'strike': '500',
                'option_type': 'CE',
                'tradingsymbol': 'RECLTD26MAR500CE2',
                'token': '115',
                'lotsize': '25'
            },
            {
                'symbol': 'RECLTD',
                'instrument': 'OPTSTK',
                'exchange': 'NFO',
                'expiry': '2026-03-26',
                'strike': '510',
                'option_type': 'CE',
                'tradingsymbol': 'RECLTD26MAR510CE2',
                'token': '116',
                'lotsize': '25'
            },
            {
                'symbol': 'RECLTD',
                'instrument': 'OPTSTK',
                'exchange': 'NFO',
                'expiry': '2026-03-26',
                'strike': '520',
                'option_type': 'CE',
                'tradingsymbol': 'RECLTD26MAR520CE',
                'token': '113',
                'lotsize': '25'
            },
            {
                'symbol': 'RECLTD',
                'instrument': 'OPTSTK',
                'exchange': 'NFO',
                'expiry': '2026-03-26',
                'strike': '520',
                'option_type': 'PE',
                'tradingsymbol': 'RECLTD26MAR520PE',
                'token': '114',
                'lotsize': '25'
            }
        ]

    def test_select_expiry_weekly_and_monthly(self):
        master = FakeMaster(self._make_rows())
        resolver = ContractResolver(master)

        weekly_next = resolver._select_expiry('RECLTD', 'weekly+1', 'OPTSTK')
        monthly = resolver._select_expiry('RECLTD', 'monthly', 'OPTSTK')

        self.assertEqual(weekly_next, datetime.date(2026, 3, 12))
        self.assertEqual(monthly, datetime.date(2026, 3, 26))

    def test_resolve_option_symbol_atm_offset(self):
        master = FakeMaster(self._make_rows())
        resolver = ContractResolver(master)

        res = resolver.resolve_option_symbol('RECLTD', ltp=513, option_type='CE', strike_logic='ATM+1', expiry_type='monthly')
        self.assertTrue(res['ok'])
        self.assertEqual(res['tradingsymbol'], 'RECLTD26MAR520CE')
        self.assertEqual(res['token'], '113')


if __name__ == '__main__':
    unittest.main()
