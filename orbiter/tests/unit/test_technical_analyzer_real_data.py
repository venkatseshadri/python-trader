import unittest
import json
import os
from orbiter.core.engine.rule.fact_converter import FactConverter
from orbiter.core.engine.rule.technical_analyzer import TechnicalAnalyzer


class TestTechnicalAnalyzerRealData(unittest.TestCase):
    def test_indicators_on_real_candles(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        path = os.path.join(project_root, 'orbiter', 'tests', 'data', 'RECLTD_2024-07-25.json')

        with open(path, 'r') as f:
            raw_data = json.load(f)

        # Build broker-style candle dicts
        raw = []
        for row in raw_data:
            raw.append({
                'intc': str(row['close']),
                'inth': str(row['high']),
                'intl': str(row['low']),
                'into': str(row['open']),
                'v': str(row['volume']),
                'stat': 'Ok',
            })

        fc = FactConverter(project_root=project_root)
        std = fc.convert_candle_data(raw)

        ta = TechnicalAnalyzer()
        indicators = ta.analyze(std)

        # Validate key indicators exist and are numeric
        self.assertIn('ema5', indicators)
        self.assertIn('rsi', indicators)
        self.assertIn('atr', indicators)
        self.assertGreater(indicators['ema5'], 0.0)
        self.assertGreaterEqual(indicators['rsi'], 0.0)
        self.assertGreater(indicators['atr'], 0.0)


if __name__ == '__main__':
    unittest.main()
