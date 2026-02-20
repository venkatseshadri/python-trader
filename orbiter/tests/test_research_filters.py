import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import os
import datetime
import json
from orbiter.filters.tp.f4_dynamic_budget import DynamicBudgetTP
from orbiter.filters.sl.f11_ema20_mortality import trend_mortality_sl, resample_to_15min
from orbiter.core.broker.resolver import ContractResolver

class TestResearchFiltersRealData(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Use the small pre-filtered JSON file
        cls.json_path = os.path.join(os.path.dirname(__file__), '../../backtest_lab/data/intraday1pct/ADANIENT/ADANIENT_2026-01-21.json')
        if not os.path.exists(cls.json_path):
            raise unittest.SkipTest(f"Data file not found: {cls.json_path}")
        
        with open(cls.json_path, 'r') as f:
            cls.raw_data = json.load(f)
        
        cls.day_data = pd.DataFrame(cls.raw_data)

    def setUp(self):
        self.dynamic_tp = DynamicBudgetTP()
        self.symbol = "ADANIENT"

    def test_dynamic_tp_against_real_adani_orb(self):
        """Verify Dynamic TP logic using real ADANIENT ORB levels."""
        orb_data = self.day_data[self.day_data['date'].str.contains(' 09:1[5-9]:| 09:2[0-9]:| 09:30:')]
        if orb_data.empty:
            self.skipTest("No ORB data found")
            
        orb_high = orb_data['high'].max()
        orb_low = orb_data['low'].min()
        orb_size_pct = (orb_high - orb_low) / orb_low * 100.0
        
        entry_price = orb_high + 0.1
        position = {
            'token': f'NSE|{self.symbol}', 'symbol': self.symbol,
            'orb_high': orb_high, 'orb_low': orb_low,
            'entry_price': entry_price, 'strategy': 'FUTURE_LONG'
        }
        
        res = self.dynamic_tp.evaluate(position, entry_price * 1.05, {})
        self.assertIn('hit', res)

    def test_trend_mortality_on_real_resampled_data(self):
        """Verify EMA20 Mortality SL using resampled real data."""
        minute_candles = []
        for item in self.raw_data:
            minute_candles.append({
                'time': item['date'], 'into': item['open'], 'inth': item['high'],
                'intl': item['low'], 'intc': item['close'], 'v': item['volume'], 'stat': 'Ok'
            })
            
        position = {'strategy': 'FUTURE_LONG', 'symbol': self.symbol}
        data = {'candles': minute_candles}
        current_ltp = minute_candles[-1]['intc']
        
        res = trend_mortality_sl(position, current_ltp, data)
        self.assertIn('hit', res)

class TestContractResolverFixed(unittest.TestCase):
    def setUp(self):
        self.mock_master = MagicMock()
        self.mock_master.DERIVATIVE_LOADED = True
        self.resolver = ContractResolver(self.mock_master)

    def test_select_expiry_monthly(self):
        """Verify monthly expiry selection without TypeError"""
        exp1, exp2 = '2026-02-19', '2026-02-26'
        self.mock_master.DERIVATIVE_OPTIONS = [
            {'symbol': 'SBIN', 'instrument': 'OPTSTK', 'exchange': 'NFO', 'expiry': exp1},
            {'symbol': 'SBIN', 'instrument': 'OPTSTK', 'exchange': 'NFO', 'expiry': exp2}
        ]
        self.mock_master._parse_expiry_date.side_effect = lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date()
        
        class FakeDate(datetime.date):
            @classmethod
            def today(cls): return datetime.date(2026, 2, 1)

        with patch('orbiter.core.broker.resolver.datetime.date', FakeDate):
            res = self.resolver._select_expiry('SBIN', 'monthly', 'OPTSTK')
            self.assertEqual(res, datetime.date(2026, 2, 26))

if __name__ == '__main__':
    unittest.main()
