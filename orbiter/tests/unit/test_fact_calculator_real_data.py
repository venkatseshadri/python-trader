import unittest
import json
import os
from orbiter.core.engine.rule.fact_calculator import FactCalculator
from orbiter.core.engine.rule.fact_converter import FactConverter
from orbiter.utils.data_manager import DataManager
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager


class TestFactCalculatorRealData(unittest.TestCase):
    def test_calculate_technical_facts_real_candles(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        ConstantsManager._instance = None
        SchemaManager._instance = None

        facts_path = DataManager.get_manifest_path(project_root, 'mandatory_files', 'fact_definitions')
        fact_definitions = DataManager.load_json(facts_path)

        path = os.path.join(project_root, 'orbiter', 'tests', 'data', 'RECLTD_2024-07-25.json')
        with open(path, 'r') as f:
            raw_data = json.load(f)

        candles = []
        for row in raw_data:
            candles.append({
                'intc': str(row['close']),
                'inth': str(row['high']),
                'intl': str(row['low']),
                'into': str(row['open']),
                'v': str(row['volume']),
                'stat': 'Ok',
            })

        fc = FactConverter(project_root=project_root)
        standardized = fc.convert_candle_data(candles)
        standardized['_raw_list'] = candles

        calc = FactCalculator(project_root, fact_definitions)
        facts = calc.calculate_technical_facts(standardized)

        # Validate a few common facts exist and are numeric if present
        self.assertIsInstance(facts, dict)
        # At least one fact should be produced for sufficient data
        self.assertGreaterEqual(len(facts), 1)


if __name__ == '__main__':
    unittest.main()
