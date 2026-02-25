import unittest
import json
import os
from types import SimpleNamespace
from orbiter.core.engine.rule.rule_manager import RuleManager
from orbiter.core.engine.session.session_manager import SessionManager
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager


class TestRuleManagerRealData(unittest.TestCase):
    def test_evaluate_and_score_real_data(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        ConstantsManager._instance = None
        SchemaManager._instance = None

        session = SessionManager(project_root, simulation=True)
        rules_path = os.path.join(project_root, session.get_active_rules_file())
        manager = RuleManager(project_root, rules_path, session)

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

        token = 'NSE|RECLTD'
        client = SimpleNamespace(SYMBOLDICT={token: {'symbol': 'RECLTD', 'candles': candles}})
        state = SimpleNamespace(client=client, active_positions=[])
        source = SimpleNamespace(state=state)

        actions = manager.evaluate(source, context=manager.constants.get('fact_contexts', 'instrument_context'), token=token)
        score = manager.evaluate_score(source, context=manager.constants.get('fact_contexts', 'instrument_context'), token=token)

        self.assertIsInstance(actions, list)
        self.assertIsInstance(score, float)


if __name__ == '__main__':
    unittest.main()
