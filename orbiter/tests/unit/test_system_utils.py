
import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import sys

# Precise Path Resolution
current_dir = os.path.dirname(os.path.abspath(__file__))
# current_dir: project_root/orbiter/tests/unit
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from orbiter.utils.system import bootstrap
from orbiter.utils.lock import manage_lockfile, LOCK_ACQUIRE, LOCK_RELEASE
from orbiter.utils.argument_parser import ArgumentParser

class TestSystemUtils(unittest.TestCase):

    def setUp(self):
        self.mock_manifest = {
            "app_name": "TEST",
            "structure": {
                "package": "orbiter",
                "config": "orbiter/config",
                "rules": "orbiter/rules",
                "logs": "logs/system"
            },
            "mandatory_files": {
                "system_config": "orbiter/config/system.json",
                "session_config": "orbiter/config/session.json"
            },
            "settings": {
                "lock_file": ".test.lock"
            }
        }

    @patch('orbiter.utils.lock.DataManager.load_manifest')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.getpid')
    def test_acquire_lock_success(self, mock_pid, mock_file, mock_exists, mock_load_manifest):
        """Case: No lock file exists -> Success."""
        mock_load_manifest.return_value = self.mock_manifest
        mock_exists.return_value = False
        mock_pid.return_value = 1234
        
        manage_lockfile("/fake/root", LOCK_ACQUIRE)
        # lock_rel_path is .test.lock
        mock_file.assert_any_call(os.path.join("/fake/root", ".test.lock"), 'w')
        mock_file().write.assert_called_once_with("1234")

    @patch('orbiter.utils.lock.logging.getLogger')
    @patch('orbiter.utils.lock.DataManager.load_manifest')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="5678")
    @patch('os.kill')
    def test_acquire_lock_collision(self, mock_kill, mock_file, mock_exists, mock_load_manifest, mock_logger):
        """Case: Lock exists and process is alive -> Raise RuntimeError."""
        mock_load_manifest.return_value = self.mock_manifest
        mock_exists.return_value = True
        mock_kill.return_value = None # Alive
        
        with self.assertRaises(RuntimeError) as cm:
            manage_lockfile("/fake/root", LOCK_ACQUIRE)
        self.assertIn("Another instance is already running", str(cm.exception))

    @patch('os.path.isdir')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"strategyId": "sys_strat"}')
    def test_parse_cli_explicit_boolean_and_strategy(self, mock_file, mock_exists, mock_isdir):
        """Verify explicit true/false values and strategyId assignments."""
        mock_exists.return_value = True
        mock_isdir.return_value = True
        args = ["--simulation=false", "--strategyId=my_strat"]
        facts = ArgumentParser.parse_cli_to_facts(args, project_root="/fake/root")
        
        self.assertFalse(facts.get('simulation'))
        self.assertEqual(facts.get('strategyid'), 'my_strat')

    @patch('os.path.isdir')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"strategyId": "sys_strat"}')
    def test_parse_cli_case_insensitivity(self, mock_file, mock_exists, mock_isdir):
        """Verify that boolean values are case insensitive, but string values preserve their case."""
        mock_exists.return_value = True
        mock_isdir.return_value = True
        args = ["--simulation=TRUE", "--strategyId=My_Strat_ID"]
        facts = ArgumentParser.parse_cli_to_facts(args, project_root="/fake/root")
        
        self.assertTrue(facts.get('simulation'))
        self.assertEqual(facts.get('strategyid'), 'My_Strat_ID')

    @patch('os.path.isdir')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"strategyId": "sys_strat"}')
    def test_parse_cli_ignore_extras(self, mock_file, mock_exists, mock_isdir):
        """Verify that any arguments beyond the first two are entirely ignored."""
        mock_exists.return_value = True
        mock_isdir.return_value = True
        args = ["--simulation=true", "--strategyId=strat1", "--extraArg=foo"]
        facts = ArgumentParser.parse_cli_to_facts(args, project_root="/fake/root")
        
        self.assertTrue(facts.get('simulation'))
        self.assertEqual(facts.get('strategyid'), 'strat1')
        self.assertNotIn('extraarg', facts)

    @patch('os.path.isdir')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"strategyId": "default_from_sys"}')
    def test_parse_cli_defaults_when_missing_or_unmatched(self, mock_file, mock_exists, mock_isdir):
        """Verify defaults are applied if arguments are omitted and system.json is used."""
        mock_exists.return_value = True
        mock_isdir.return_value = True
        args = ["--unrelated=foo"]
        facts = ArgumentParser.parse_cli_to_facts(args, project_root="/fake/root")
        
        self.assertTrue(facts.get('simulation'))
        self.assertEqual(facts.get('strategyid'), 'default_from_sys')
        self.assertEqual(facts.get('unrelated'), 'foo')

    @patch('os.path.isdir')
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='{"strategyId": "fallback_strat"}')
    @patch('orbiter.utils.argument_parser.logging.getLogger')
    def test_parse_cli_invalid_strategy_falls_back_to_default(self, mock_logger, mock_file, mock_exists, mock_isdir):
        """Verify that an invalid or missing strategyId logs a warning and falls back to system default."""
        # Setup: system.json exists, but strategy dir does not exist
        def mock_exists_side_effect(path):
            if "system.json" in path: return True
            if "fallback_strat" in path: return True
            return False # Strategy folder missing
            
        def mock_isdir_side_effect(path):
            if "fallback_strat" in path: return True
            return False

        mock_exists.side_effect = mock_exists_side_effect
        mock_isdir.side_effect = mock_isdir_side_effect
        
        # Test 1: Invalid strategy provided
        args = ["--simulation=true", "--strategyId=invalid_strat"]
        facts = ArgumentParser.parse_cli_to_facts(args, project_root="/fake/root")
        
        self.assertEqual(facts.get('strategyid'), 'fallback_strat')
        mock_logger().warning.assert_any_call("Strategy 'invalid_strat' not found at /fake/root/orbiter/strategies/invalid_strat. Falling back to default.")

        # Test 2: Missing strategyId entirely
        args_missing = ["--simulation=true"]
        facts_missing = ArgumentParser.parse_cli_to_facts(args_missing, project_root="/fake/root")
        
        # Should not warn about "Strategy 'None' not found"
        self.assertEqual(facts_missing.get('strategyid'), 'fallback_strat')

    @patch('orbiter.utils.system.DataManager.load_manifest')
    @patch('orbiter.utils.system.resolve_project_root')
    def test_bootstrap_success(self, mock_resolve, mock_load_manifest):
        """Verify bootstrap success sequence."""
        mock_resolve.return_value = "/fake/root"
        mock_load_manifest.return_value = self.mock_manifest
        
        root = bootstrap()
        
        self.assertEqual(root, "/fake/root")

if __name__ == '__main__':
    unittest.main()
