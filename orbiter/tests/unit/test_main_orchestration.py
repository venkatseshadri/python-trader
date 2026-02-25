import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure project root is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from package
from orbiter.main import run_orchestrator
from orbiter.utils.lock import LOCK_ACQUIRE, LOCK_RELEASE

class TestMainOrchestration(unittest.TestCase):
    
    @patch('orbiter.main.setup_logging')
    @patch('orbiter.main.manage_lockfile')
    @patch('orbiter.main.bootstrap')
    @patch('orbiter.main.ArgumentParser.parse_cli_to_facts')
    @patch('orbiter.main.OrbiterApp')
    def test_run_orchestrator_success_flow(self, mock_app_class, mock_parse, mock_bootstrap, mock_lock, mock_logging):
        """Scenario: Everything works correctly."""
        mock_root = "/fake/root"
        mock_context = {'simulation': True}
        mock_bootstrap.return_value = mock_root
        mock_parse.return_value = mock_context
        
        # We need to make sure project_root inside main is handled
        # But we mocked bootstrap, so it returns mock_root
        
        run_orchestrator()
        
        # Verify calls. Use assert_called_with for precision
        mock_lock.assert_any_call(unittest.mock.ANY, LOCK_ACQUIRE)
        mock_app_class.return_value.run.assert_called_once()
        mock_lock.assert_any_call(unittest.mock.ANY, LOCK_RELEASE)

    @patch('orbiter.main.setup_logging')
    @patch('orbiter.main.manage_lockfile')
    @patch('orbiter.main.bootstrap')
    @patch('orbiter.main.ArgumentParser.parse_cli_to_facts')
    def test_run_orchestrator_lock_collision(self, mock_parse, mock_bootstrap, mock_lock, mock_logging):
        """Scenario: Lock already held by another process."""
        mock_bootstrap.return_value = "/root"
        mock_parse.return_value = {}
        
        def side_effect(root, action):
            if action == LOCK_ACQUIRE:
                raise RuntimeError("Collision")
            return None
            
        mock_lock.side_effect = side_effect
        
        with self.assertRaises(RuntimeError):
            run_orchestrator()
            
        # Verify RELEASE was never called because acquisition failed
        release_calls = [call for call in mock_lock.call_args_list if call.args[1] == LOCK_RELEASE]
        self.assertEqual(len(release_calls), 0)

if __name__ == '__main__':
    unittest.main()
