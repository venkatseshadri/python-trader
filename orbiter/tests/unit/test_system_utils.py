
import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import sys
import importlib

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
        """Verify that any arguments beyond the first five are entirely ignored."""
        mock_exists.return_value = True
        mock_isdir.return_value = True
        args = ["--simulation=true", "--strategyId=strat1", "--strategyExecution=fixed", "--unknown=value", "--extraArg=foo"]
        facts = ArgumentParser.parse_cli_to_facts(args, project_root="/fake/root")
        
        self.assertTrue(facts.get('simulation'))
        self.assertEqual(facts.get('strategyid'), 'strat1')
        self.assertEqual(facts.get('strategy_execution'), 'fixed')
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

    @patch('orbiter.utils.system.ConfigLoader.load_manifest')
    @patch('orbiter.utils.system.get_project_root')
    def test_bootstrap_success(self, mock_get_root, mock_load_manifest):
        """Verify bootstrap success sequence."""
        mock_get_root.return_value = "/fake/root"
        mock_load_manifest.return_value = self.mock_manifest
        
        root, context = bootstrap()
        
        self.assertEqual(root, "/fake/root")
        self.assertIn('simulation', context)

    # =========================================================================
    # Tests for get_project_root() - Direct unit tests
    # =========================================================================

    @patch('os.path.dirname', side_effect=lambda x: x.replace('/orbiter/utils/system.py', '').replace('/orbiter/utils', '').replace('/orbiter', ''))
    def test_get_project_root_script_mode(self, mock_dirname):
        """Test get_project_root() when running as Python script."""
        import orbiter.utils.system as system_module
        
        # Reset global
        system_module.PROJECT_ROOT = None
        
        # Mock sys.frozen = False (script mode)
        with patch('sys.frozen', False, create=True):
            with patch('sys.path', []):
                result = system_module.get_project_root()
        
        # Expected: /home/trading_ceo/python-trader (3 levels up from utils/system.py)
        self.assertIn("trading_ceo", result)

    def test_get_project_root_frozen_mode(self):
        """Test get_project_root() when running as PyInstaller binary."""
        import orbiter.utils.system as system_module
        
        # Reset global
        system_module.PROJECT_ROOT = None
        
        # Temporarily set sys.frozen
        original_frozen = getattr(sys, 'frozen', False)
        original_executable = sys.executable
        
        try:
            sys.frozen = True
            sys.executable = '/opt/orbiter/bin/orbiter'
            # Clear sys.path to test the path insertion logic
            original_path = sys.path.copy()
            sys.path = []
            result = system_module.get_project_root()
        finally:
            # Restore
            if original_frozen:
                sys.frozen = original_frozen
            else:
                if hasattr(sys, 'frozen'):
                    delattr(sys, 'frozen')
            sys.executable = original_executable
            sys.path[:] = original_path
        
        # /opt/orbiter/bin/orbiter -> parent is /opt/orbiter/bin -> parent is /opt/orbiter
        self.assertEqual(result, "/opt/orbiter")

    def test_get_project_root_returns_same_instance(self):
        """Test that get_project_root() returns the same instance on repeated calls."""
        import orbiter.utils.system as system_module
        
        # Store original
        original_root = system_module.get_project_root()
        
        # Call again
        second_call = system_module.get_project_root()
        
        # Should be the same
        self.assertEqual(original_root, second_call)

    def test_get_project_root_adds_to_sys_path(self):
        """Test that get_project_root() adds PROJECT_ROOT to sys.path."""
        import orbiter.utils.system as system_module
        
        # Get current sys.path
        original_path = sys.path.copy()
        
        root = system_module.get_project_root()
        
        # PROJECT_ROOT should now be in sys.path
        self.assertIn(root, sys.path)

    # =========================================================================
    # Tests for get_manifest()
    # =========================================================================

    def test_get_manifest_returns_loaded_manifest(self):
        """Test get_manifest() returns MANIFEST global."""
        import orbiter.utils.system as system_module
        
        # Set a mock manifest
        test_manifest = {"app_name": "TEST", "version": "1.0"}
        system_module.MANIFEST = test_manifest
        
        result = system_module.get_manifest()
        
        self.assertEqual(result, test_manifest)

    def test_get_manifest_returns_empty_when_not_loaded(self):
        """Test get_manifest() returns empty dict when MANIFEST is empty."""
        import orbiter.utils.system as system_module
        
        # Reset manifest
        system_module.MANIFEST = {}
        
        result = system_module.get_manifest()
        
        self.assertEqual(result, {})

    # =========================================================================
    # Tests for get_constants()
    # =========================================================================

    def test_get_constants_returns_loaded_constants(self):
        """Test get_constants() returns CONSTANTS global."""
        import orbiter.utils.system as system_module
        
        # Set mock constants
        test_constants = {"max_retries": 3, "timeout": 30}
        system_module.CONSTANTS = test_constants
        
        result = system_module.get_constants()
        
        self.assertEqual(result, test_constants)

    def test_get_constants_returns_empty_when_not_loaded(self):
        """Test get_constants() returns empty dict when CONSTANTS is empty."""
        import orbiter.utils.system as system_module
        
        # Reset constants
        system_module.CONSTANTS = {}
        
        result = system_module.get_constants()
        
        self.assertEqual(result, {})

    # =========================================================================
    # Tests for get_global_config()
    # =========================================================================

    def test_get_global_config_returns_loaded_config(self):
        """Test get_global_config() returns GLOBAL_CONFIG global."""
        import orbiter.utils.system as system_module
        
        # Set mock config
        test_config = {"log_level": "INFO", "debug": False}
        system_module.GLOBAL_CONFIG = test_config
        
        result = system_module.get_global_config()
        
        self.assertEqual(result, test_config)

    def test_get_global_config_returns_empty_when_not_loaded(self):
        """Test get_global_config() returns empty dict when GLOBAL_CONFIG is empty."""
        import orbiter.utils.system as system_module
        
        # Reset global config
        system_module.GLOBAL_CONFIG = {}
        
        result = system_module.get_global_config()
        
        self.assertEqual(result, {})

    # =========================================================================
    # Tests for bootstrap() edge cases
    # =========================================================================

    @patch('orbiter.utils.system.get_project_root')
    @patch('orbiter.utils.system.ConfigLoader.load_manifest')
    def test_bootstrap_manifest_missing(self, mock_load_manifest, mock_get_root):
        """Test bootstrap() when manifest.json is missing."""
        mock_get_root.return_value = "/fake/root"
        mock_load_manifest.return_value = {}  # Empty manifest
        
        root, context = bootstrap()
        
        self.assertEqual(root, "/fake/root")
        self.assertEqual(context, {})  # Empty context on failure

    @patch('orbiter.utils.system.get_project_root')
    @patch('orbiter.utils.system.ConfigLoader.load_manifest')
    @patch('orbiter.utils.system.ConfigLoader.load_config')
    @patch('orbiter.utils.system.ArgumentParser.parse_cli_to_facts')
    def test_bootstrap_full_flow(self, mock_parse, mock_load_config, mock_load_manifest, mock_get_root):
        """Test bootstrap() full initialization flow."""
        mock_get_root.return_value = "/fake/root"
        mock_load_manifest.return_value = self.mock_manifest
        mock_load_config.side_effect = [
            {"max_retries": 3},  # constants
            {"log_level": "INFO"}  # global_config
        ]
        mock_parse.return_value = {"simulation": True, "strategyid": "test"}
        
        root, context = bootstrap()
        
        self.assertEqual(root, "/fake/root")
        self.assertEqual(context["simulation"], True)
        self.assertEqual(context["strategyid"], "test")


if __name__ == '__main__':
    unittest.main()
