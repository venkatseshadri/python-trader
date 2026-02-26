import unittest
import json
import os
import numpy as np
import talib
from orbiter.filters.sl.f1_price_increase_10 import check_sl


class TestSmartATRSLFilter(unittest.TestCase):
    def test_future_nominal_sl_real_data(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        path = os.path.join(project_root, 'orbiter', 'tests', 'data', 'RECLTD_2024-07-25.json')
        with open(path, 'r') as f:
            data = json.load(f)

        closes = np.array([row['close'] for row in data], dtype=float)
        highs = np.array([row['high'] for row in data], dtype=float)
        lows = np.array([row['low'] for row in data], dtype=float)

        atr = talib.ATR(highs, lows, closes, timeperiod=14)
        entry_atr = float(atr[-1]) if not np.isnan(atr[-1]) else 0.0

        entry_price = float(closes[0])
        current_ltp = float(min(closes))
        lot_size = 100

        position = {
            'strategy': 'FUTURE_LONG',
            'entry_price': entry_price,
            'entry_atr': entry_atr,
            'lot_size': lot_size,
            'future_max_loss_pct': 5.0,
        }

        tick_data = {'lp': str(current_ltp)}
        res = check_sl(tick_data, position=position)
        self.assertIn('hit', res)
        self.assertIn('reason', res)


if __name__ == '__main__':
    unittest.main()
