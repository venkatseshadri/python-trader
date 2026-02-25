import unittest
import json
import os
from orbiter.filters.tp.f3_retracement_sl import check_retracement_sl


class TestRetracementSLFilter(unittest.TestCase):
    def test_retracement_real_data(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        path = os.path.join(project_root, 'orbiter', 'tests', 'data', 'RECLTD_2024-07-25.json')
        with open(path, 'r') as f:
            data = json.load(f)

        closes = [row['close'] for row in data]
        entry = closes[0]
        peak = max(closes)
        current = closes[-1]
        lot = 50

        position = {
            'max_pnl_rs': (peak - entry) * lot,
            'entry_net_premium': entry,
            'lot_size': lot,
            'tsl_retracement_pct': 50,
            'tsl_activation_rs': 1000,
        }
        data_ctx = {'current_net_premium': current}

        res = check_retracement_sl(position, current, data_ctx)
        self.assertIn('hit', res)
        self.assertIn('reason', res)


if __name__ == '__main__':
    unittest.main()
