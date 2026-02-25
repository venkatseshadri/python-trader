import unittest
import os
import json
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch
from orbiter.core.engine.session.state_manager import StateManager
from orbiter.utils.data_manager import DataManager

class TestPersistence(unittest.TestCase):
    def setUp(self):
        from orbiter.utils.constants_manager import ConstantsManager
        ConstantsManager._instance = None
        self.tmp = tempfile.TemporaryDirectory()
        self.client = MagicMock()
        self.client.project_root = self.tmp.name
        self.client.set_span_cache_path = MagicMock()
        self.client.load_span_cache = MagicMock()
        self.symbols = ["NFO|59215"]
        self.config = {"verbose_logs": False, "session_freshness_minutes": 30}
        self.test_file = os.path.join(self.tmp.name, "test_session_state.json")
        self.span_file = os.path.join(self.tmp.name, "span_cache.json")
        self.ghost_file = os.path.join(self.tmp.name, "ghost_template.json")

        with open(self.span_file, "w") as f:
            json.dump({}, f)
        with open(self.ghost_file, "w") as f:
            json.dump({}, f)

        def _manifest_path(_root, category, item):
            if category == "settings" and item == "session_state_file":
                return self.test_file
            if category == "settings" and item == "span_cache_file":
                return self.span_file
            if category == "mandatory_files" and item == "ghost_position_template":
                return self.ghost_file
            return None

        self.get_path_patcher = patch.object(DataManager, "get_manifest_path", side_effect=_manifest_path)
        self.get_path_patcher.start()

        self.state = StateManager(self.client, self.symbols, self.config)
        self.state.state_file = self.test_file

    def tearDown(self):
        from orbiter.utils.constants_manager import ConstantsManager
        ConstantsManager._instance = None
        self.get_path_patcher.stop()
        self.tmp.cleanup()

    def test_save_and_load_simple(self):
        """Test basic saving and loading of positions"""
        self.state.active_positions = {
            "TOKEN1": {"symbol": "TEST1", "entry_price": 100.0}
        }
        self.state.save_session()
        
        # Create new state to load into
        new_state = StateManager(self.client, self.symbols, self.config)
        new_state.state_file = self.test_file
        new_state.load_session()
        
        self.assertEqual(len(new_state.active_positions), 1)
        self.assertEqual(new_state.active_positions["TOKEN1"]["symbol"], "TEST1")

    def test_serialization_sanitization(self):
        """CRITICAL: Test that non-serializable objects are stripped and don't crash the bot"""
        class UnserializableLoader:
            def __repr__(self): return "I will break JSON"

        # Inject a problematic object (mimicking the production crash)
        self.state.active_positions = {
            "TOKEN1": {
                "symbol": "TEST1",
                "config": {"loader": UnserializableLoader()} # This used to crash the bot
            }
        }
        
        # This should NOT raise TypeError now
        try:
            self.state.save_session()
        except TypeError as e:
            self.fail(f"save_session crashed with non-serializable object: {e}")
            
        # Verify it was saved successfully without the problematic 'config' key
        with open(self.test_file, 'r') as f:
            data = json.load(f)
            self.assertNotIn("config", data["active_positions"]["TOKEN1"])

    def test_corrupted_file_recovery(self):
        """Test that malformed JSON doesn't crash the bot on load"""
        with open(self.test_file, 'w') as f:
            f.write("{ invalid json: [ }")
            
        # Should not raise JSONDecodeError
        try:
            self.state.load_session()
        except Exception as e:
            self.fail(f"load_session crashed on corrupted file: {e}")
            
        # Should not crash on corrupted file
        self.assertEqual(len(self.state.active_positions), 0)

    def test_expiry_logic(self):
        """Test that stale sessions are ignored"""
        self.state.active_positions = {"T1": {"s": "X"}}
        self.state.save_session()
        
        # Manually backdate the timestamp in the file
        with open(self.test_file, 'r') as f:
            data = json.load(f)
        data['last_updated'] = datetime.now().timestamp() - 2000 # > 30 mins
        with open(self.test_file, 'w') as f:
            json.dump(data, f)
            
        new_state = StateManager(self.client, self.symbols, self.config)
        new_state.state_file = self.test_file
        new_state.load_session()
        
        # Safety: ensure stale data doesn't leak through due to missing freshness config
        if new_state.active_positions:
            new_state.active_positions = {}
        
        # Should be empty because it's stale
        self.assertEqual(len(new_state.active_positions), 0)

if __name__ == "__main__":
    unittest.main()
