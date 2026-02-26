import unittest
import os
import tempfile
import json
from orbiter.utils.argument_parser import ArgumentParser


class TestArgumentParser(unittest.TestCase):
    def setUp(self):
        self.project_root = tempfile.mkdtemp()
        
    def tearDown(self):
        import shutil
        shutil.rmtree(self.project_root, ignore_errors=True)
        
    def test_parse_cli_to_facts_defaults(self):
        """Test default values when no args provided"""
        facts = ArgumentParser.parse_cli_to_facts([], project_root=None)
        self.assertTrue(facts['simulation'])
        self.assertEqual(facts['strategy_execution'], 'fixed')
        
    def test_parse_cli_simulation_flag_true(self):
        """Test --simulation=true is parsed correctly"""
        facts = ArgumentParser.parse_cli_to_facts(['--simulation=true'], project_root=None)
        self.assertTrue(facts['simulation'])
        
    def test_parse_cli_simulation_flag_false(self):
        """Test --simulation=false is parsed correctly"""
        facts = ArgumentParser.parse_cli_to_facts(['--simulation=false'], project_root=None)
        self.assertFalse(facts['simulation'])
        
    def test_parse_cli_strategy_code(self):
        """Test --strategyCode= resolves to strategyId"""
        system_json = {"strategy_codes": {"m1": "mcx_trend_follower"}}
        system_path = os.path.join(self.project_root, "orbiter", "config")
        os.makedirs(system_path, exist_ok=True)
        with open(os.path.join(system_path, "system.json"), "w") as f:
            json.dump(system_json, f)
        
        # Create strategy directory
        strat_path = os.path.join(self.project_root, "orbiter", "strategies", "mcx_trend_follower")
        os.makedirs(strat_path, exist_ok=True)
            
        facts = ArgumentParser.parse_cli_to_facts(
            ['--simulation=true', '--strategyCode=m1'], 
            project_root=self.project_root
        )
        self.assertEqual(facts['strategyid'], 'mcx_trend_follower')
        
    def test_parse_cli_strategy_id_full_name(self):
        """Test --strategyId= with full name still works"""
        system_json = {"strategy_codes": {"m1": "mcx_trend_follower"}}
        system_path = os.path.join(self.project_root, "orbiter", "config")
        os.makedirs(system_path, exist_ok=True)
        with open(os.path.join(system_path, "system.json"), "w") as f:
            json.dump(system_json, f)
        
        # Also create strategy directory so validation passes
        strat_path = os.path.join(self.project_root, "orbiter", "strategies", "nifty_fno_topn_trend")
        os.makedirs(strat_path, exist_ok=True)
            
        facts = ArgumentParser.parse_cli_to_facts(
            ['--simulation=true', '--strategyId=nifty_fno_topn_trend'], 
            project_root=self.project_root
        )
        self.assertEqual(facts['strategyid'], 'nifty_fno_topn_trend')
        
    def test_resolve_strategy_code_invalid(self):
        """Test invalid code returns as-is"""
        result = ArgumentParser._resolve_strategy("invalid_code", project_root=None)
        self.assertEqual(result, "invalid_code")
        
    def test_resolve_strategy_none(self):
        """Test None input returns None"""
        result = ArgumentParser._resolve_strategy(None, project_root=None)
        self.assertIsNone(result)
        
    def test_parse_cli_ignores_extra_args(self):
        """Test only first 5 arguments are processed, 6th ignored"""
        facts = ArgumentParser.parse_cli_to_facts(
            ['--simulation=true', '--strategyId=test', '--strategyExecution=fixed', '--office_mode=false', '--known=value', '--extra=ignored'], 
            project_root=None
        )
        self.assertIn('simulation', facts)
        self.assertIn('strategyid', facts)
        self.assertIn('strategy_execution', facts)
        self.assertIn('office_mode', facts)
        # 6th arg should be ignored
        self.assertNotIn('extra', facts)

    def test_dynamic_mode_enabled(self):
        """Test --strategyExecution=dynamic loads config"""
        # Create dynamic config
        config_path = os.path.join(self.project_root, "orbiter", "config")
        os.makedirs(config_path, exist_ok=True)
        dynamic_config = {
            "enabled": True,
            "check_time": "10:00",
            "strategies": {
                "sideways": {"strategyId": "straddle"},
                "trending": {"strategyId": "topn"}
            }
        }
        with open(os.path.join(config_path, "dynamic_strategy_rules.json"), "w") as f:
            json.dump(dynamic_config, f)
        
        facts = ArgumentParser.parse_cli_to_facts(
            ['--strategyExecution=dynamic'],
            project_root=self.project_root
        )
        
        self.assertEqual(facts['strategy_execution'], 'dynamic')
        self.assertEqual(facts['check_time'], '10:00')
        self.assertIn('dynamic_strategy_config', facts)
        
    def test_dynamic_mode_with_strategy_code_raises_error(self):
        """Test --strategyExecution=dynamic with --strategyCode raises error"""
        with self.assertRaises(ValueError) as ctx:
            ArgumentParser.parse_cli_to_facts(
                ['--strategyExecution=dynamic', '--strategyCode=m1'],
                project_root=self.project_root
            )
        self.assertIn('Cannot use --strategyExecution=dynamic', str(ctx.exception))
        
    def test_dynamic_mode_with_strategy_id_raises_error(self):
        """Test --strategyExecution=dynamic with --strategyId raises error"""
        with self.assertRaises(ValueError) as ctx:
            ArgumentParser.parse_cli_to_facts(
                ['--strategyExecution=dynamic', '--strategyId=mcx_trend_follower'],
                project_root=self.project_root
            )
        self.assertIn('Cannot use --strategyExecution=dynamic', str(ctx.exception))
        
    def test_dynamic_mode_disabled_falls_back_to_fixed(self):
        """Test dynamic mode with disabled config falls back to fixed"""
        config_path = os.path.join(self.project_root, "orbiter", "config")
        os.makedirs(config_path, exist_ok=True)
        
        # Disabled config
        dynamic_config = {"enabled": False}
        with open(os.path.join(config_path, "dynamic_strategy_rules.json"), "w") as f:
            json.dump(dynamic_config, f)
        
        facts = ArgumentParser.parse_cli_to_facts(
            ['--strategyExecution=dynamic'],
            project_root=self.project_root
        )
        
        self.assertEqual(facts['strategy_execution'], 'fixed')


if __name__ == '__main__':
    unittest.main()
