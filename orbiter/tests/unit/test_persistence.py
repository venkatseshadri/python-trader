import unittest
import os
import json
from datetime import datetime
from orbiter.core.engine.state import OrbiterState
from unittest.mock import MagicMock

class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.client = MagicMock()
        self.symbols = ["NFO|59215"]
        self.config = {"VERBOSE_LOGS": False}
        self.state = OrbiterState(self.client, self.symbols, MagicMock(), self.config)
        self.test_file = "orbiter/data/test_session_state.json"
        self.state.state_file = self.test_file

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        if os.path.exists(self.test_file + ".tmp"):
            os.remove(self.test_file + ".tmp")
        if os.path.exists(self.test_file + ".corrupt"):
            os.remove(self.test_file + ".corrupt")

    def test_save_and_load_simple(self):
        """Test basic saving and loading of positions"""
        self.state.active_positions = {
            "TOKEN1": {"symbol": "TEST1", "entry_price": 100.0}
        }
        self.state.save_session()
        
        # Create new state to load into
        new_state = OrbiterState(self.client, self.symbols, MagicMock(), self.config)
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
            
        # Should have moved the file to .corrupt
        self.assertTrue(os.path.exists(self.test_file + ".corrupt"))

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
            
        new_state = OrbiterState(self.client, self.symbols, MagicMock(), self.config)
        new_state.state_file = self.test_file
        new_state.load_session()
        
        # Should be empty because it's stale
        self.assertEqual(len(new_state.active_positions), 0)

if __name__ == "__main__":
    unittest.main()
