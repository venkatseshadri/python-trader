import unittest
import json
import os
from orbiter.config.mcx.config import SYMBOLS_FUTURE_UNIVERSE

class TestMCXParity(unittest.TestCase):
    def test_config_matches_json_map(self):
        """Verify that the SYMBOLS_FUTURE_UNIVERSE list in config.py matches the keys in mcx_futures_map.json"""
        
        # 1. Load the JSON Map
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        map_path = os.path.join(base_dir, 'data', 'mcx_futures_map.json')
        
        self.assertTrue(os.path.exists(map_path), f"MCX map file missing at {map_path}")
        
        with open(map_path, 'r') as f:
            map_data = json.load(f)
        
        # 2. Extract Prefixed Keys (e.g., 'MCX|467013')
        # The JSON map stores raw tokens as keys, but config uses prefixed ones
        map_tokens = {f"MCX|{k}" for k in map_data.keys()}
        config_tokens = set(SYMBOLS_FUTURE_UNIVERSE)
        
        # 3. Verify Parity
        missing_in_config = map_tokens - config_tokens
        extra_in_config = config_tokens - map_tokens
        
        self.assertEqual(len(missing_in_config), 0, f"Tokens in JSON map but MISSING from config.py: {missing_in_config}")
        self.assertEqual(len(extra_in_config), 0, f"Tokens in config.py but MISSING from JSON map: {extra_in_config}")
        
        # 4. Basic Integrity: Ensure we have the 15 expected tokens
        self.assertEqual(len(config_tokens), 15, f"Expected 15 MCX tokens, found {len(config_tokens)}")

if __name__ == '__main__':
    unittest.main()
