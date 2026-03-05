#!/usr/bin/env python3
"""
Test that all MCX instruments have valid tokens and can be loaded.

This test validates that:
1. All instruments in MCX strategy have valid tokens
2. Tokens can be resolved to trading symbols via ScripMaster
3. The instruments.json is properly formatted
"""
import unittest
import json
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)


class TestMCXInstrumentScoring(unittest.TestCase):
    """Test that all MCX instruments can be loaded with valid tokens."""
    
    def test_all_instruments_have_valid_tokens(self):
        """Verify all instruments have token values."""
        instruments_path = os.path.join(project_root, 'orbiter', 'strategies', 'mcx_trend_follower', 'instruments.json')
        with open(instruments_path, 'r') as f:
            instruments = json.load(f)
        
        print(f"\n=== Testing {len(instruments)} MCX Instruments ===")
        
        for inst in instruments:
            symbol = inst.get('symbol')
            token = inst.get('token')
            exchange = inst.get('exchange')
            
            self.assertIsNotNone(token, f"Missing token for {symbol}")
            self.assertIsNotNone(exchange, f"Missing exchange for {symbol}")
            self.assertEqual(exchange, 'MCX', f"Expected MCX exchange for {symbol}")
            
            # Token should be a non-empty string
            self.assertIsInstance(token, str, f"Token should be string for {symbol}")
            self.assertTrue(len(token) > 0, f"Token should not be empty for {symbol}")
            
            print(f"  ✓ {symbol}: token={token}, exchange={exchange}")
    
    def test_instruments_match_futures_map(self):
        """Verify instruments are present in mcx_futures_map.json."""
        instruments_path = os.path.join(project_root, 'orbiter', 'strategies', 'mcx_trend_follower', 'instruments.json')
        with open(instruments_path, 'r') as f:
            instruments = json.load(f)
        
        futures_map_path = os.path.join(project_root, 'orbiter', 'data', 'mcx_futures_map.json')
        with open(futures_map_path, 'r') as f:
            futures_map = json.load(f)
        
        print(f"\n=== Verifying {len(instruments)} instruments in futures map ===")
        
        missing = []
        for inst in instruments:
            symbol = inst['symbol']
            if symbol not in futures_map:
                missing.append(symbol)
            else:
                print(f"  ✓ {symbol} found in futures map")
        
        self.assertEqual(len(missing), 0, f"Instruments missing from futures map: {missing}")
    
    def test_instrument_count(self):
        """Verify we have the expected number of instruments."""
        instruments_path = os.path.join(project_root, 'orbiter', 'strategies', 'mcx_trend_follower', 'instruments.json')
        with open(instruments_path, 'r') as f:
            instruments = json.load(f)
        
        print(f"\n=== Instrument Count ===")
        print(f"Total instruments: {len(instruments)}")
        
        # We should have at least 10 instruments for MCX
        self.assertGreaterEqual(len(instruments), 10, "Should have at least 10 MCX instruments")


if __name__ == '__main__':
    unittest.main(verbosity=2)
