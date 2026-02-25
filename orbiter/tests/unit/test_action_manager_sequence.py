import unittest
from unittest.mock import MagicMock
from orbiter.core.engine.action.action_manager import ActionManager
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager


class TestActionManagerSequence(unittest.TestCase):
    def setUp(self):
        # Reset singletons
        ConstantsManager._instance = None
        SchemaManager._instance = None
        self.manager = ActionManager()

    def test_executes_in_sequence_order(self):
        calls = []

        def a1(**params):
            calls.append(("a1", params.get("v")))

        def a2(**params):
            calls.append(("a2", params.get("v")))

        self.manager.register_action("A1", a1)
        self.manager.register_action("A2", a2)

        actions = [
            {"type": "A1", "sequence": 2, "params": {"v": 2}},
            {"type": "A2", "sequence": 1, "params": {"v": 1}},
        ]

        self.manager.execute_batch(actions)
        self.assertEqual(calls, [("a2", 1), ("a1", 2)])


if __name__ == "__main__":
    unittest.main()
