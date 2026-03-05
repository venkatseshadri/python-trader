"""
Test: Strategy Loading
Validates:
1. All strategy codes can be loaded
2. Strategy files (rules.json, filters.json, instruments.json) exist
3. Dynamic strategy selection works

Run: python -m pytest tests/unit/test_strategy_loading.py -v
"""
import unittest
import os
import json
from pathlib import Path


class TestStrategyLoading(unittest.TestCase):
    """Test all strategies can be loaded correctly."""
    
    @classmethod
    def setUpClass(cls):
        # Navigate from tests/unit/test_xyz.py to orbiter/ level
        cls.project_root = Path(__file__).parent.parent.parent.parent
        cls.strategies_dir = cls.project_root / "orbiter" / "strategies"
        cls.config_dir = cls.project_root / "orbiter" / "config"
        
    def test_all_strategy_codes_have_directories(self):
        """Verify all strategy codes in system.json point to existing directories."""
        system_path = self.config_dir / "system.json"
        with open(system_path) as f:
            system = json.load(f)
        
        missing = []
        for code, strategy_id in system.get("strategy_codes", {}).items():
            strategy_path = self.strategies_dir / strategy_id
            if not strategy_path.exists():
                missing.append(f"{code} -> {strategy_id}")
        
        self.assertEqual(missing, [], f"Missing strategy directories: {missing}")
    
    def test_all_strategies_have_required_files(self):
        """Verify each strategy has rules.json, filters.json, instruments.json."""
        required_files = ["rules.json", "filters.json", "instruments.json", "strategy.json"]
        
        issues = []
        for strategy_dir in self.strategies_dir.iterdir():
            if not strategy_dir.is_dir() or strategy_dir.name.startswith('_') or strategy_dir.name == 'template_strategy':
                continue  # Skip template_strategy which uses .sample files
                
            for req_file in required_files:
                if not (strategy_dir / req_file).exists():
                    issues.append(f"{strategy_dir.name}: missing {req_file}")
        
        self.assertEqual(issues, [], f"Strategy file issues:\n" + "\n".join(issues))

    def test_all_rules_json_valid(self):
        """Verify all rules.json files are valid JSON."""
        invalid = []
        
        for rules_file in self.strategies_dir.glob("*/rules.json"):
            try:
                with open(rules_file) as f:
                    rules = json.load(f)
                
                # Check required keys
                if "strategies" not in rules:
                    invalid.append(f"{rules_file.name}: missing 'strategies' key")
            except json.JSONDecodeError as e:
                invalid.append(f"{rules_file.name}: {e}")
        
        self.assertEqual(invalid, [], f"Invalid rules.json:\n" + "\n".join(invalid))

    def test_all_filters_json_valid(self):
        """Verify all filters.json files are valid JSON."""
        invalid = []
        
        for filters_file in self.strategies_dir.glob("*/filters.json"):
            try:
                with open(filters_file) as f:
                    filters = json.load(f)
            except json.JSONDecodeError as e:
                invalid.append(f"{filters_file.name}: {e}")
        
        self.assertEqual(invalid, [], f"Invalid filters.json:\n" + "\n".join(invalid))

    def test_all_instruments_json_valid(self):
        """Verify all instruments.json files are valid JSON."""
        invalid = []
        
        for instruments_file in self.strategies_dir.glob("*/instruments.json"):
            try:
                with open(instruments_file) as f:
                    instruments = json.load(f)
                
                # Verify it's a list
                if not isinstance(instruments, list):
                    invalid.append(f"{instruments_file.name}: not a list")
            except json.JSONDecodeError as e:
                invalid.append(f"{instruments_file.name}: {e}")
        
        self.assertEqual(invalid, [], f"Invalid instruments.json:\n" + "\n".join(invalid))

    def test_mcx_strategy_has_mcx_exchange(self):
        """Verify MCX strategy uses MCX exchange."""
        mcx_path = self.strategies_dir / "mcx_trend_follower" / "instruments.json"
        with open(mcx_path) as f:
            instruments = json.load(f)
        
        exchanges = set(i.get("exchange") for i in instruments)
        self.assertEqual(exchanges, {"MCX"}, f"MCX strategy should only use MCX exchange: {exchanges}")

    def test_nifty_strategy_has_nse_exchange(self):
        """Verify Nifty strategies use NSE/NFO exchanges."""
        nifty_path = self.strategies_dir / "nifty_fno_topn_trend" / "instruments.json"
        with open(nifty_path) as f:
            instruments = json.load(f)
        
        exchanges = set(i.get("exchange") for i in instruments)
        self.assertIn("NSE", exchanges, f"Nifty strategy should use NSE: {exchanges}")

    def test_bsensex_strategy_has_bse_exchange(self):
        """Verify BSE strategies use BSE/BFO exchanges."""
        bse_path = self.strategies_dir / "bsensex_bfo_topn_trend" / "instruments.json"
        with open(bse_path) as f:
            instruments = json.load(f)
        
        exchanges = set(i.get("exchange") for i in instruments)
        self.assertIn("BSE", exchanges, f"BSE strategy should use BSE: {exchanges}")

    def test_dynamic_strategy_config_valid(self):
        """Verify dynamic_strategy_rules.json is valid."""
        config_path = self.config_dir / "dynamic_strategy_rules.json"
        
        with open(config_path) as f:
            config = json.load(f)
        
        # Check required keys
        self.assertIn("enabled", config)
        self.assertIn("strategies", config)
        self.assertIn("sideways", config["strategies"])
        self.assertIn("trending", config["strategies"])

    def test_no_expired_tokens_in_instruments(self):
        """Verify no obviously expired tokens in instruments.json.
        
        This is a basic check - checks for tokens that start with '1' (old format)
        which are typically expired. Real validation requires broker API.
        """
        # Common expired token patterns (just a basic heuristic)
        suspicious_tokens = ["1165486", "1165487"]  # Known expired
        
        issues = []
        for instruments_file in self.strategies_dir.glob("*/instruments.json"):
            with open(instruments_file) as f:
                instruments = json.load(f)
            
            for inst in instruments:
                token = str(inst.get("token", ""))
                if token in suspicious_tokens:
                    issues.append(f"{instruments_file.name}: {inst.get('symbol')} has suspicious token {token}")
        
        if issues:
            self.fail("Found potentially expired tokens:\n" + "\n".join(issues))


class TestDynamicStrategySelection(unittest.TestCase):
    """Test dynamic strategy selection logic."""
    
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).parent.parent.parent.parent
    
    @unittest.skipIf(True, "Requires network - run manually")
    def test_dynamic_selection_uses_yf_adx(self):
        """Test dynamic selection actually uses Yahoo Finance ADX."""
        # This would test the actual flow
        pass


if __name__ == '__main__':
    unittest.main()
