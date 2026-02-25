import unittest
import json
import os
from orbiter.core.engine.rule.fact_converter import FactConverter


class TestFactConverter(unittest.TestCase):
    def test_convert_candle_data_real_file(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        fc = FactConverter(project_root=project_root)

        path = os.path.join(project_root, 'orbiter', 'tests', 'data', 'RECLTD_2024-07-25.json')
        with open(path, 'r') as f:
            raw_data = json.load(f)

        raw = []
        for row in raw_data[:50]:
            raw.append({
                'intc': str(row['close']),
                'inth': str(row['high']),
                'intl': str(row['low']),
                'into': str(row['open']),
                'v': str(row['volume']),
                'stat': 'Ok',
            })

        data = fc.convert_candle_data(raw)
        self.assertEqual(len(data["close"]), len(raw))
        self.assertGreater(float(data["high"][-1]), 0.0)
        self.assertGreater(float(data["low"][0]), 0.0)


if __name__ == "__main__":
    unittest.main()
