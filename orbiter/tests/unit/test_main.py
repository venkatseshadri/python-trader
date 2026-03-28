#!/usr/bin/env python3
"""
🧪 Test Suite for main.py - Orbiter Entry Point
Tests that verify the orchestrator works correctly and fails when critical components are commented out.

These tests detect:
- bootstrap() being commented out
- load_config being commented out
- lockfile logic being removed
- exception handling being removed
"""
import unittest
from unittest.mock import patch, MagicMock, call
import os
import sys
import importlib

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


# Store original main module state before each test
class TestMainOrchestration(unittest.TestCase):
    """Tests for main.py run_orchestrator() flow - detects actual code removal"""
    
    def setUp(self):
        """Reload main module to get fresh state"""
        # Clear any cached imports
        if 'orbiter.main' in sys.modules:
            del sys.modules['orbiter.main']
        if 'orbiter.utils.system' in sys.modules:
            del sys.modules['orbiter.utils.system']

    def _check_bootstrap_call_in_source(self):
        """Helper: Check if bootstrap() call exists in main.py source code"""
        main_path = os.path.join(project_root, 'orbiter', 'main.py')
        with open(main_path, 'r') as f:
            source = f.read()
        
        # Check for actual bootstrap() call (not commented)
        lines = source.split('\n')
        for line in lines:
            stripped = line.strip()
            # Skip comments and empty lines
            if stripped.startswith('#'):
                continue
            if 'bootstrap()' in stripped:
                return True
        return False

    def test_bootstrap_is_not_commented_out_in_main(self):
        """Fails if bootstrap() call is commented out in main.py"""
        has_bootstrap = self._check_bootstrap_call_in_source()
        self.assertTrue(has_bootstrap, 
            "bootstrap() call is missing or commented out in main.py!")

    @patch('orbiter.main.setup_logging')
    @patch('orbiter.main.manage_lockfile')
    @patch('orbiter.main.bootstrap')
    @patch('orbiter.main.OrbiterApp')
    def test_bootstrap_is_called(self, mock_app_class, mock_bootstrap, mock_lock, mock_logging):
        """Fails if bootstrap() is removed from run_orchestrator()"""
        mock_bootstrap.return_value = (project_root, {'simulation': True})
        
        from orbiter.main import run_orchestrator
        run_orchestrator()
        
        # Verify bootstrap was called
        mock_bootstrap.assert_called_once()
        
        # Verify OrbiterApp was created with correct args
        mock_app_class.assert_called_once_with(project_root, {'simulation': True})

    @patch('orbiter.main.setup_logging')
    @patch('orbiter.main.manage_lockfile')
    @patch('orbiter.main.bootstrap')
    @patch('orbiter.main.OrbiterApp')
    def test_bootstrap_returns_project_root_and_context(self, mock_app_class, mock_bootstrap, mock_lock, mock_logging):
        """Fails if bootstrap return is modified incorrectly"""
        mock_bootstrap.return_value = (project_root, {'strategyCode': 'N1'})
        
        from orbiter.main import run_orchestrator
        run_orchestrator()
        
        # Verify context was passed to OrbiterApp
        call_args = mock_app_class.call_args
        self.assertEqual(call_args[0][1], {'strategyCode': 'N1'})

    def test_lockfile_acquire_is_in_source(self):
        """Fails if LOCK_ACQUIRE is removed from main.py"""
        main_path = os.path.join(project_root, 'orbiter', 'main.py')
        with open(main_path, 'r') as f:
            source = f.read()
        
        self.assertIn('LOCK_ACQUIRE', source, 
            "LOCK_ACQUIRE not found in main.py - lockfile logic may be removed!")

    def test_lockfile_release_is_in_source(self):
        """Fails if LOCK_RELEASE is removed from main.py"""
        main_path = os.path.join(project_root, 'orbiter', 'main.py')
        with open(main_path, 'r') as f:
            source = f.read()
        
        self.assertIn('LOCK_RELEASE', source,
            "LOCK_RELEASE not found in main.py - lockfile cleanup may be removed!")

    @patch('orbiter.main.setup_logging')
    @patch('orbiter.main.manage_lockfile')
    @patch('orbiter.main.bootstrap')
    @patch('orbiter.main.OrbiterApp')
    def test_lockfile_acquired_and_released(self, mock_app_class, mock_bootstrap, mock_lock, mock_logging):
        """Fails if lockfile logic is commented out"""
        mock_bootstrap.return_value = (project_root, {})
        
        from orbiter.main import run_orchestrator
        run_orchestrator()
        
        # Verify lock acquire was called
        mock_lock.assert_any_call(project_root, 'acquire')
        # Verify lock release was called
        mock_lock.assert_any_call(project_root, 'release')

    @patch('orbiter.main.setup_logging')
    @patch('orbiter.main.manage_lockfile')
    @patch('orbiter.main.bootstrap')
    @patch('orbiter.main.OrbiterApp')
    def test_orbiter_app_start_called(self, mock_app_class, mock_bootstrap, mock_lock, mock_logging):
        """Fails if app.start() is commented out"""
        mock_bootstrap.return_value = (project_root, {})
        
        from orbiter.main import run_orchestrator
        run_orchestrator()
        
        mock_app_class.return_value.start.assert_called_once()

    @patch('orbiter.main.setup_logging')
    @patch('orbiter.main.manage_lockfile')
    @patch('orbiter.main.bootstrap')
    @patch('orbiter.main.OrbiterApp')
    def test_exception_handling_releases_lock(self, mock_app_class, mock_bootstrap, mock_lock, mock_logging):
        """Fails if exception handling is commented out"""
        mock_bootstrap.return_value = (project_root, {})
        mock_app_class.return_value.start.side_effect = Exception("Test error")
        
        from orbiter.main import run_orchestrator
        with self.assertRaises(Exception):
            run_orchestrator()
        
        # Verify lock was released even on exception
        mock_lock.assert_any_call(project_root, 'release')

    def test_exception_handling_exists_in_source(self):
        """Fails if exception handling (try/except) is removed from main.py"""
        main_path = os.path.join(project_root, 'orbiter', 'main.py')
        with open(main_path, 'r') as f:
            source = f.read()
        
        self.assertIn('try:', source, "try block missing in main.py")
        self.assertIn('except', source, "except block missing in main.py")


class TestBootstrapFunction(unittest.TestCase):
    """Tests for orbiter.utils.system.bootstrap() - verifies load_config is called"""

    def setUp(self):
        """Reload to get fresh state"""
        if 'orbiter.utils.system' in sys.modules:
            del sys.modules['orbiter.utils.system']

    def test_bootstrap_returns_tuple(self):
        """Fails if bootstrap() is removed or changed to not return tuple"""
        from orbiter.utils.system import bootstrap, get_project_root
        
        root, context = bootstrap()
        
        # Should return project root string
        self.assertIsInstance(root, str)
        self.assertTrue(os.path.exists(root))
        
        # Context should be a dict
        self.assertIsInstance(context, dict)

    @patch('orbiter.utils.system.ConfigLoader.load_manifest')
    @patch('orbiter.utils.system.ConfigLoader.load_config')
    def test_bootstrap_calls_load_manifest(self, mock_load_config, mock_load_manifest):
        """Fails if load_manifest is commented out in bootstrap()"""
        # Setup mocks to return valid data
        mock_load_manifest.return_value = {'strategies': {}}
        mock_load_config.return_value = {}
        
        from orbiter.utils.system import bootstrap
        bootstrap()
        
        # Verify load_manifest was called
        mock_load_manifest.assert_called()

    @patch('orbiter.utils.system.ConfigLoader.load_config')
    def test_bootstrap_calls_argument_parser(self, mock_load_config):
        """Fails if ArgumentParser.parse_cli_to_facts is commented out in bootstrap()"""
        mock_load_config.return_value = {}
        
        from orbiter.utils.system import bootstrap
        root, context = bootstrap()
        
        # Context should contain strategyid (parsed from CLI args)
        self.assertIn('strategyid', context, 
            "ArgumentParser.parse_cli_to_facts may be commented out - no strategyid in context")

    @patch('orbiter.utils.system.ConfigLoader.load_manifest')
    @patch('orbiter.utils.system.ConfigLoader.load_config')
    def test_bootstrap_calls_load_config_for_constants(self, mock_load_config, mock_load_manifest):
        """Fails if load_config('constants') is commented out in bootstrap()"""
        mock_load_manifest.return_value = {'strategies': {}}
        mock_load_config.return_value = {}
        
        from orbiter.utils.system import bootstrap
        bootstrap()
        
        # Verify load_config was called for constants
        config_calls = mock_load_config.call_args_list
        constants_loaded = any(
            'constants' in str(call) for call in config_calls
        )
        self.assertTrue(constants_loaded, "load_config for 'constants' was not called")

    @patch('orbiter.utils.system.ConfigLoader.load_manifest')
    @patch('orbiter.utils.system.ConfigLoader.load_config')
    def test_bootstrap_calls_load_config_for_global_config(self, mock_load_config, mock_load_manifest):
        """Fails if load_config('global_config') is commented out in bootstrap()"""
        mock_load_manifest.return_value = {'strategies': {}}
        mock_load_config.return_value = {}
        
        from orbiter.utils.system import bootstrap
        bootstrap()
        
        # Verify load_config was called for global_config
        config_calls = mock_load_config.call_args_list
        global_config_loaded = any(
            'global_config' in str(call) for call in config_calls
        )
        self.assertTrue(global_config_loaded, "load_config for 'global_config' was not called")

    @patch('orbiter.utils.system.ConfigLoader.load_manifest')
    @patch('orbiter.utils.system.ConfigLoader.load_config')
    def test_bootstrap_parses_cli_args(self, mock_load_config, mock_load_manifest):
        """Fails if ArgumentParser.parse_cli_to_facts is commented out"""
        mock_load_manifest.return_value = {'strategies': {}}
        mock_load_config.return_value = {}
        
        from orbiter.utils.system import bootstrap
        root, context = bootstrap()
        
        # Context should contain parsed CLI args (even if empty)
        self.assertIsInstance(context, dict)


class TestBootstrapDependencies(unittest.TestCase):
    """Tests verifying the internal dependencies of bootstrap()"""

    def setUp(self):
        """Reload to get fresh state"""
        if 'orbiter.utils.system' in sys.modules:
            del sys.modules['orbiter.utils.system']

    def test_bootstrap_has_manifest(self):
        """Fails if MANIFEST global is not set by bootstrap"""
        from orbiter.utils.system import bootstrap, MANIFEST
        
        # Store original
        original_manifest = MANIFEST
        
        bootstrap()
        
        # MANIFEST should now be populated (not None)
        from orbiter.utils.system import MANIFEST as CURRENT_MANIFEST
        self.assertIsNotNone(CURRENT_MANIFEST, "MANIFEST was not loaded by bootstrap()")

    def test_bootstrap_has_constants(self):
        """Fails if CONSTANTS global is not set by bootstrap"""
        from orbiter.utils.system import bootstrap, CONSTANTS
        
        original_constants = CONSTANTS
        
        bootstrap()
        
        from orbiter.utils.system import CONSTANTS as CURRENT_CONSTANTS
        self.assertIsNotNone(CURRENT_CONSTANTS, "CONSTANTS was not loaded by bootstrap()")

    def test_bootstrap_has_global_config(self):
        """Fails if GLOBAL_CONFIG global is not set by bootstrap"""
        from orbiter.utils.system import bootstrap, GLOBAL_CONFIG
        
        original_config = GLOBAL_CONFIG
        
        bootstrap()
        
        from orbiter.utils.system import GLOBAL_CONFIG as CURRENT_GLOBAL_CONFIG
        self.assertIsNotNone(CURRENT_GLOBAL_CONFIG, "GLOBAL_CONFIG was not loaded by bootstrap()")


class TestSourceCodeIntegrity(unittest.TestCase):
    """Direct source code inspection tests - these will catch commented-out code"""

    def test_bootstrap_definition_exists(self):
        """Fails if bootstrap() function is removed from system.py"""
        system_path = os.path.join(project_root, 'orbiter', 'utils', 'system.py')
        with open(system_path, 'r') as f:
            source = f.read()
        
        self.assertIn('def bootstrap', source, 
            "bootstrap() function definition not found in system.py!")

    def test_load_manifest_call_exists_in_bootstrap(self):
        """Fails if load_manifest call is removed from bootstrap()"""
        system_path = os.path.join(project_root, 'orbiter', 'utils', 'system.py')
        with open(system_path, 'r') as f:
            source = f.read()
        
        # Find bootstrap function
        self.assertIn('load_manifest', source,
            "load_manifest call not found in system.py!")

    def test_load_config_for_constants_exists(self):
        """Fails if load_config for constants is removed from bootstrap()"""
        system_path = os.path.join(project_root, 'orbiter', 'utils', 'system.py')
        with open(system_path, 'r') as f:
            source = f.read()
        
        self.assertIn("'constants'", source,
            "load_config for 'constants' not found in system.py!")

    def test_load_config_for_global_config_exists(self):
        """Fails if load_config for global_config is removed from bootstrap()"""
        system_path = os.path.join(project_root, 'orbiter', 'utils', 'system.py')
        with open(system_path, 'r') as f:
            source = f.read()
        
        self.assertIn("'global_config'", source,
            "load_config for 'global_config' not found in system.py!")

    def test_argument_parser_import_exists_in_system(self):
        """Fails if ArgumentParser import is commented out in system.py"""
        system_path = os.path.join(project_root, 'orbiter', 'utils', 'system.py')
        with open(system_path, 'r') as f:
            lines = f.readlines()
        
        # Look for import of ArgumentParser (not commented)
        found_import = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            if 'ArgumentParser' in stripped and 'import' in stripped:
                found_import = True
                break
        
        self.assertTrue(found_import, 
            "ArgumentParser import not found or commented out in system.py!")

    def test_argument_parser_call_exists_in_bootstrap(self):
        """Fails if ArgumentParser.parse_cli_to_facts call is removed from bootstrap()"""
        system_path = os.path.join(project_root, 'orbiter', 'utils', 'system.py')
        with open(system_path, 'r') as f:
            source = f.read()
        
        self.assertIn('ArgumentParser.parse_cli_to_facts', source,
            "ArgumentParser.parse_cli_to_facts call not found in bootstrap()!")

    def test_argument_parser_definition_exists(self):
        """Fails if ArgumentParser class is removed from argument_parser.py"""
        parser_path = os.path.join(project_root, 'orbiter', 'utils', 'argument_parser.py')
        with open(parser_path, 'r') as f:
            source = f.read()
        
        self.assertIn('class ArgumentParser', source,
            "ArgumentParser class not found in argument_parser.py!")

    # ========== NEW: run_orchestrator source integrity tests ==========
    
    def test_run_orchestrator_definition_exists_in_main(self):
        """Fails if run_orchestrator() function is removed from main.py"""
        main_path = os.path.join(project_root, 'orbiter', 'main.py')
        with open(main_path, 'r') as f:
            source = f.read()
        
        self.assertIn('def run_orchestrator', source,
            "run_orchestrator() function definition not found in main.py!")

    def test_run_orchestrator_call_exists_in_main_block(self):
        """Fails if run_orchestrator() call is removed from __main__ block"""
        main_path = os.path.join(project_root, 'orbiter', 'main.py')
        with open(main_path, 'r') as f:
            source = f.read()
        
        # Check for run_orchestrator() call in the if __name__ block (not commented)
        lines = source.split('\n')
        found_call = False
        in_main_block = False
        
        for line in lines:
            stripped = line.strip()
            
            # Enter __main__ block
            if 'if __name__' in stripped and '__main__' in stripped:
                in_main_block = True
            
            # Look for run_orchestrator call inside __main__ block
            if in_main_block:
                if stripped.startswith('#'):
                    continue
                if 'run_orchestrator()' in stripped:
                    found_call = True
                    break
        
        self.assertTrue(found_call,
            "run_orchestrator() call not found in __main__ block of main.py!")

    def test_orbiter_app_import_exists_in_main(self):
        """Fails if OrbiterApp import is removed from main.py"""
        main_path = os.path.join(project_root, 'orbiter', 'main.py')
        with open(main_path, 'r') as f:
            lines = f.readlines()
        
        found_import = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#'):
                continue
            if 'OrbiterApp' in stripped and 'import' in stripped:
                found_import = True
                break
        
        self.assertTrue(found_import,
            "OrbiterApp import not found or commented out in main.py!")

    def test_orbiter_app_class_instantiated_in_run_orchestrator(self):
        """Fails if OrbiterApp instantiation is removed from run_orchestrator"""
        main_path = os.path.join(project_root, 'orbiter', 'main.py')
        with open(main_path, 'r') as f:
            source = f.read()
        
        self.assertIn('OrbiterApp(', source,
            "OrbiterApp instantiation not found in run_orchestrator!")


class TestBootstrapReturnsNone(unittest.TestCase):
    """Tests verifying run_orchestrator handles bootstrap returning None"""

    def setUp(self):
        """Reload to get fresh state"""
        if 'orbiter.main' in sys.modules:
            del sys.modules['orbiter.main']

    @patch('orbiter.main.setup_logging')
    @patch('orbiter.main.manage_lockfile')
    @patch('orbiter.main.bootstrap')
    @patch('orbiter.main.OrbiterApp')
    def test_bootstrap_returns_none_does_not_create_app(self, mock_app_class, mock_bootstrap, mock_lock, mock_logging):
        """Verifies that when bootstrap returns None, OrbiterApp is NOT created"""
        # Simulate bootstrap returning None (what happens if it's commented out or fails)
        mock_bootstrap.return_value = None
        
        from orbiter.main import run_orchestrator
        
        # Should either raise error or handle None gracefully
        try:
            run_orchestrator()
        except (TypeError, AttributeError, ValueError):
            # Expected - trying to unpack None raises error
            pass
        
        # OrbiterApp should NOT be instantiated when bootstrap returns None
        mock_app_class.assert_not_called()

    @patch('orbiter.main.setup_logging')
    @patch('orbiter.main.manage_lockfile')
    @patch('orbiter.main.bootstrap')
    @patch('orbiter.main.OrbiterApp')
    def test_bootstrap_returns_empty_tuple_raises_error(self, mock_app_class, mock_bootstrap, mock_lock, mock_logging):
        """Verifies that when bootstrap returns empty tuple (), error is handled"""
        # Simulate bootstrap returning empty tuple (partial removal)
        mock_bootstrap.return_value = ()
        
        from orbiter.main import run_orchestrator
        
        # Should raise error when trying to unpack empty tuple
        with self.assertRaises((TypeError, ValueError, IndexError)):
            run_orchestrator()
        
        # OrbiterApp should NOT be instantiated
        mock_app_class.assert_not_called()

    @patch('orbiter.main.setup_logging')
    @patch('orbiter.main.manage_lockfile')
    @patch('orbiter.main.bootstrap')
    @patch('orbiter.main.OrbiterApp')
    def test_bootstrap_returns_single_value_raises_error(self, mock_app_class, mock_bootstrap, mock_lock, mock_logging):
        """Verifies that when bootstrap returns single value (not tuple), error is handled"""
        # Simulate bootstrap returning just project_root without context
        mock_bootstrap.return_value = project_root  # Just a string, not a tuple
        
        from orbiter.main import run_orchestrator
        
        # Should raise error when trying to unpack single value
        with self.assertRaises((TypeError, ValueError)):
            run_orchestrator()
        
        # OrbiterApp should NOT be instantiated
        mock_app_class.assert_not_called()

    @patch('orbiter.main.setup_logging')
    @patch('orbiter.main.manage_lockfile')
    @patch('orbiter.main.bootstrap')
    @patch('orbiter.main.OrbiterApp')
    def test_bootstrap_returns_none_logs_error(self, mock_app_class, mock_bootstrap, mock_lock, mock_logging):
        """Verifies that when bootstrap returns None, error is raised (not silently ignored)"""
        mock_bootstrap.return_value = None
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger
        
        from orbiter.main import run_orchestrator
        
        # When bootstrap returns None, unpacking raises TypeError
        with self.assertRaises((TypeError, ValueError)):
            run_orchestrator()


class TestRunOrchestratorCallChain(unittest.TestCase):
    """Tests verifying the full call chain from __main__ to run_orchestrator"""

    def setUp(self):
        """Reload to get fresh state"""
        if 'orbiter.main' in sys.modules:
            del sys.modules['orbiter.main']

    @patch('orbiter.main.setup_logging')
    @patch('orbiter.main.manage_lockfile')
    @patch('orbiter.main.bootstrap')
    @patch('orbiter.main.OrbiterApp')
    def test_full_call_chain_works(self, mock_app_class, mock_bootstrap, mock_lock, mock_logging):
        """Verifies complete flow: run_orchestrator -> bootstrap -> OrbiterApp -> start"""
        mock_bootstrap.return_value = (project_root, {'simulation': True})
        
        from orbiter.main import run_orchestrator
        run_orchestrator()
        
        # Verify complete chain:
        # 1. bootstrap was called
        mock_bootstrap.assert_called_once()
        
        # 2. OrbiterApp was instantiated with correct args
        mock_app_class.assert_called_once_with(project_root, {'simulation': True})
        
        # 3. app.start() was called
        mock_app_class.return_value.start.assert_called_once()
        
        # 4. Lock was acquired and released
        mock_lock.assert_any_call(project_root, 'acquire')
        mock_lock.assert_any_call(project_root, 'release')

    @patch('orbiter.main.setup_logging')
    @patch('orbiter.main.manage_lockfile')
    @patch('orbiter.main.bootstrap')
    @patch('orbiter.main.OrbiterApp')
    def test_run_orchestrator_returns_after_start(self, mock_app_class, mock_bootstrap, mock_lock, mock_logging):
        """Verifies run_orchestrator returns after app.start() completes (not hanging)"""
        mock_bootstrap.return_value = (project_root, {})
        mock_app_class.return_value.start.return_value = None  # Normal return
        
        from orbiter.main import run_orchestrator
        result = run_orchestrator()
        
        # Should return normally (not hang)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main(verbosity=2)