import unittest
from unittest.mock import MagicMock, patch
import datetime
from orbiter.core.broker.resolver import ContractResolver

class TestContractResolver(unittest.TestCase):

    def setUp(self):
        self.mock_master = MagicMock()
        self.mock_master.DERIVATIVE_LOADED = True
        self.resolver = ContractResolver(self.mock_master)
        self.mock_api = MagicMock()

    def test_is_last_thursday(self):
        """Verify last Thursday detection logic"""
        # Feb 2026: Last Thursday is 26th
        self.assertTrue(self.resolver._is_last_thursday(datetime.date(2026, 2, 26)))
        self.assertFalse(self.resolver._is_last_thursday(datetime.date(2026, 2, 19)))

    def test_select_expiry_monthly(self):
        """Verify selection of monthly expiry (last Thursday)"""
        exp1, exp2 = '2026-02-19', '2026-02-26'
        self.mock_master.DERIVATIVE_OPTIONS = [
            {'symbol': 'SBIN', 'instrument': 'OPTSTK', 'exchange': 'NFO', 'expiry': exp1},
            {'symbol': 'SBIN', 'instrument': 'OPTSTK', 'exchange': 'NFO', 'expiry': exp2}
        ]
        # Return real date objects from mock parser
        self.mock_master._parse_expiry_date.side_effect = lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date()
        
        # Robust patch for today's date
        class FakeDate(datetime.date):
            @classmethod
            def today(cls): return datetime.date(2026, 2, 1)

        with patch('orbiter.core.broker.resolver.datetime.date', FakeDate):
            res = self.resolver._select_expiry('SBIN', 'monthly', 'OPTSTK')
            self.assertEqual(res, datetime.date(2026, 2, 26))

    def test_get_near_future_api_success(self):
        """Verify future discovery via API search"""
        self.mock_api.searchscrip.return_value = {
            'stat': 'Ok',
            'values': [
                {'instname': 'FUTSTK', 'symname': 'SBIN', 'token': '1234', 'tsym': 'SBIN-FUT', 'exp': '26-FEB-2026'}
            ]
        }
        self.mock_master._parse_expiry_date.return_value = datetime.date(2026, 2, 26)
        
        res = self.resolver.get_near_future('SBIN', 'NFO', self.mock_api)
        self.assertEqual(res['token'], 'NFO|1234')
        self.assertEqual(res['tsym'], 'SBIN-FUT')

    def test_get_credit_spread_contracts_logic(self):
        """Verify spread selection (ATM and Hedge)"""
        expiry = datetime.date(2026, 2, 26)
        self.resolver._select_expiry = MagicMock(return_value=expiry)
        self.resolver._get_option_rows = MagicMock(return_value=[
            {'tradingsymbol': 'SBIN26FEB26P600', 'strike': 600.0, 'option_type': 'PE', 'lot_size': '1500', 'exchange': 'NFO'},
            {'tradingsymbol': 'SBIN26FEB26P590', 'strike': 590.0, 'option_type': 'PE', 'lot_size': '1500', 'exchange': 'NFO'},
            {'tradingsymbol': 'SBIN26FEB26P580', 'strike': 580.0, 'option_type': 'PE', 'lot_size': '1500', 'exchange': 'NFO'}
        ])
        
        res = self.resolver.get_credit_spread_contracts('SBIN', 598.0, 'PUT', 2, 'monthly', 'OPTSTK')
        
        self.assertTrue(res['ok'])
        self.assertEqual(res['atm_strike'], 600.0)
        self.assertEqual(res['hedge_strike'], 580.0)

if __name__ == '__main__':
    unittest.main()
