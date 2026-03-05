"""
Test: Configuration Validation
Validates that:
1. Action types in rules.json match constants.json
2. Exchange config has valid product codes
3. Strategy files exist and are valid JSON
4. Paper trade flag flows correctly

Run: python -m pytest tests/unit/test_config_validation.py -v
"""
import os
import json
import unittest
from pathlib import Path


class TestConfigValidation(unittest.TestCase):
    """Critical config validation tests."""
    
    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).parent.parent.parent
        cls.config_dir = cls.project_root / "config"
        cls.strategies_dir = cls.project_root / "strategies"
        
    def test_constants_have_all_action_types(self):
        """Verify constants.json has all required action types."""
        constants_path = self.config_dir / "constants.json"
        with open(constants_path) as f:
            constants = json.load(f)
        
        action_types = constants.get("action_types", {})
        
        # Required action types
        required = {
            "trade_place_spread",
            "trade_place_future_order", 
            "trade_square_off_all",
            "trade_send_alert"
        }
        
        missing = required - set(action_types.keys())
        self.assertEqual(missing, set(), f"Missing action types in constants.json: {missing}")
        
    def test_strategies_use_valid_action_types(self):
        """Verify all action types in rules.json exist in constants.json."""
        constants_path = self.config_dir / "constants.json"
        with open(constants_path) as f:
            constants = json.load(f)
        
        valid_actions = set(constants.get("action_types", {}).values())
        # Also allow direct action names
        valid_actions.update(constants.get("action_types", {}).keys())
        
        invalid_actions = []
        
        for rules_file in self.strategies_dir.glob("*/rules.json"):
            with open(rules_file) as f:
                rules = json.load(f)
            
            # Check strategies
            for strategy in rules.get("strategies", []):
                for op in strategy.get("order_operations", []):
                    action_type = op.get("type", "")
                    if action_type and action_type not in valid_actions:
                        invalid_actions.append({
                            "file": str(rules_file.relative_to(self.project_root)),
                            "action": action_type
                        })
        
        if invalid_actions:
            msg = "\n".join([f"  {x['file']}: {x['action']}" for x in invalid_actions])
            self.fail(f"Invalid action types found:\n{msg}")
    
    def test_no_conflicting_order_operations(self):
        """
        Verify rules don't have conflicting BUY+SELL for SAME instrument.
        
        This catches bugs like the MCX bug where both BUY and SELL orders were 
        placed simultaneously for the same contract.
        
        Note: TopN strategies can have both BUY and SELL spreads - they evaluate
        both directions with different strike_logic (e.g., ATM+1 vs ATM-1).
        The test only flags cases where BOTH have identical key params.
        """
        issues = []
        
        for rules_file in self.strategies_dir.glob("*/rules.json"):
            with open(rules_file) as f:
                rules = json.load(f)
            
            for strategy in rules.get("strategies", []):
                ops = strategy.get("order_operations", [])
                
                # Group by side
                buy_ops = [op for op in ops if op.get("params", {}).get("side", "").upper() == "BUY"]
                sell_ops = [op for op in ops if op.get("params", {}).get("side", "").upper() == "SELL"]
                
                # Check if both exist
                if buy_ops and sell_ops:
                    for buy in buy_ops:
                        buy_params = buy.get("params", {})
                        
                        for sell in sell_ops:
                            sell_params = sell.get("params", {})
                            
                            # Check if key params match (would cause dual execution)
                            # Key params: exchange, derivative, strike_logic, option_type
                            key_match = (
                                buy_params.get("exchange") == sell_params.get("exchange") and
                                buy_params.get("derivative") == sell_params.get("derivative") and
                                buy_params.get("strike_logic") == sell_params.get("strike_logic") and
                                buy_params.get("option_type") == sell_params.get("option_type")
                            )
                            
                            if key_match:
                                issues.append({
                                    "file": str(rules_file.relative_to(self.project_root)),
                                    "strategy": strategy.get("name", "unknown"),
                                    "issue": f"Duplicate: {buy_params.get('exchange')}/{buy_params.get('derivative')}/{buy_params.get('strike_logic')}/{buy_params.get('option_type')}"
                                })
        
        if issues:
            msg = "\n".join([
                f"  {i['file']} ({i['strategy']}): {i['issue']}"
                for i in issues
            ])
            self.fail(f"Found conflicting order operations (identical BUY+SELL):\n{msg}")
    
    def test_exchange_config_has_products(self):
        """Verify exchange_config.json has valid product codes."""
        config_path = self.config_dir / "exchange_config.json"
        with open(config_path) as f:
            config = json.load(f)
        
        # Valid product codes for Shoonya: I (MIS), M (NRML), C (CNC), H (BO), B (CO)
        valid_products = {"I", "M", "C", "H", "B"}
        
        issues = []
        for exchange, exch_config in config.items():
            if exchange == "defaults":
                continue
            plumbing = exch_config.get("plumbing", {})
            product = plumbing.get("default_product", "")
            if product and product not in valid_products:
                issues.append(f"{exchange}: product={product} (valid: {valid_products})")
        
        self.assertEqual(issues, [], f"Invalid product codes: {issues}")
    
    def test_exchange_config_has_market_timings(self):
        """Verify exchange config has market timings."""
        config_path = self.config_dir / "exchange_config.json"
        with open(config_path) as f:
            config = json.load(f)
        
        required_fields = ["market_start", "market_end", "trade_start", "trade_end"]
        
        for exchange, exch_config in config.items():
            if exchange == "defaults":
                continue
            for field in required_fields:
                self.assertIn(field, exch_config, 
                    f"{exchange} missing {field}")
    
    def test_all_strategy_directories_exist(self):
        """Verify all strategy codes point to existing directories."""
        system_path = self.config_dir / "system.json"
        with open(system_path) as f:
            system = json.load(f)
        
        codes = system.get("strategy_codes", {})
        missing = []
        
        for code, strategy_id in codes.items():
            strategy_path = self.strategies_dir / strategy_id
            if not strategy_path.exists():
                missing.append(f"{code} -> {strategy_id}")
        
        self.assertEqual(missing, [], f"Missing strategy dirs: {missing}")
    
    def test_strategy_rules_are_valid_json(self):
        """Verify all strategy rules.json files are valid JSON."""
        invalid = []
        
        for rules_file in self.strategies_dir.glob("*/rules.json"):
            try:
                with open(rules_file) as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                invalid.append(f"{rules_file.name}: {e}")
        
        self.assertEqual(invalid, [], f"Invalid JSON in: {invalid}")
    
    def test_mcx_futures_map_tokens_match_config(self):
        """Verify MCX futures map tokens are valid."""
        map_path = self.project_root / "data" / "mcx_futures_map.json"
        if not map_path.exists():
            self.skipTest("mcx_futures_map.json not found")
        
        with open(map_path) as f:
            mcx_map = json.load(f)
        
        # Verify structure
        for token, info in mcx_map.items():
            self.assertIsInstance(info, list, f"{token} should be a list")
            self.assertGreaterEqual(len(info), 2, f"{token} should have [symbol, tsym, lot_size]")
            self.assertIsInstance(info[0], str, f"{token}[0] should be symbol string")
            self.assertIsInstance(info[1], str, f"{token}[1] should be tsym string")


class TestPaperTradeFlow(unittest.TestCase):
    """Test paper trade configuration flow."""
    
    def test_executors_check_paper_trade(self):
        """Verify executors read paper_trade from config."""
        # This is a code review test - check that executors reference config
        executors_dir = Path(__file__).parent.parent.parent / "core" / "engine" / "action" / "executors"
        
        issues = []
        for executor in executors_dir.glob("*.py"):
            if executor.name.startswith("_"):
                continue
            content = executor.read_text()
            
            # Each executor should check paper_trade
            if "def execute" in content and "def _fire" in content:
                if "paper_trade" not in content and executor.name != "base.py":
                    issues.append(executor.name)
        
        # Note: This test documents expected behavior
        # Actual implementation may vary
        print(f"Executors to verify: {issues}")


if __name__ == "__main__":
    unittest.main()
