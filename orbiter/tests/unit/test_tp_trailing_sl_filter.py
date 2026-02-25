import unittest
import json
import os
from orbiter.filters.tp.f2_trailing_sl import check_trailing_sl


class TestTrailingSLFilter(unittest.TestCase):
    def test_trailing_sl_real_data(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        path = os.path.join(project_root, 'orbiter', 'tests', 'data', 'RECLTD_2024-07-25.json')
        with open(path, 'r') as f:
            data = json.load(f)

        closes = [row['close'] for row in data]
        entry = closes[0]
        peak = max(closes)
        current = closes[-1]
        lot = 100

        position = {
            'max_pnl_rs': (peak - entry) * lot,
            'pnl_rs': (current - entry) * lot,
            'tsl_activation_rs': 1000,
            'tsl_retracement_pct': 40,
            'entry_price': entry,
        }

        res = check_trailing_sl(position, current, {})
        # We don't assert hit/no-hit; just ensure no crash and valid output
        self.assertIn('hit', res)
        self.assertIn('reason', res)


if __name__ == '__main__':
    unittest.main()
