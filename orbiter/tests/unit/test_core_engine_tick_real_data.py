import unittest
import json
import os
from types import SimpleNamespace
from orbiter.core.engine.runtime.core_engine import Engine
from orbiter.core.engine.action.action_manager import ActionManager
from orbiter.core.engine.session.session_manager import SessionManager
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager


class TestCoreEngineTickRealData(unittest.TestCase):
    def test_tick_no_crash_real_data(self):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        ConstantsManager._instance = None
        SchemaManager._instance = None

        session = SessionManager(project_root, simulation=True)
        action_manager = ActionManager()

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
        client = SimpleNamespace(
            SYMBOLDICT={token: {'symbol': 'RECLTD', 'candles': candles}},
            get_symbol=lambda tk: 'RECLTD',
            project_root=project_root
        )
        state = SimpleNamespace(client=client, symbols=[token], active_positions=[], verbose_logs=False)

        engine = Engine(state, session, action_manager, office_mode=True)
        engine.tick()


if __name__ == '__main__':
    unittest.main()
