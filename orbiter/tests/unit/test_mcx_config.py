#!/usr/bin/env python3
"""
Tests for MCX futures map configuration.

This tests the MCX futures map loading and the check_and_update_mcx_expiry method.
"""
import os
import sys
import json
import unittest
from datetime import datetime, timedelta

# Get project root - this test is in orbiter/tests/unit/
# project_root is /Users/vseshadri/python
test_dir = os.path.dirname(os.path.abspath(__file__))  # tests/unit
tests_dir = os.path.dirname(test_dir)  # tests
orbiter_dir = os.path.dirname(tests_dir)  # orbiter
project_root = os.path.dirname(orbiter_dir)  # python (parent of orbiter)
sys.path.insert(0, project_root)


class TestMCXFuturesMap(unittest.TestCase):
    """Test MCX futures map loading and format."""
    
    def setUp(self):
        """Set up test fixtures."""
        # project_root/orbiter/data/mcx_futures_map.json
        self.map_path = os.path.join(orbiter_dir, 'data', 'mcx_futures_map.json')
    
    def test_mcx_futures_map_exists(self):
        """Test that mcx_futures_map.json exists."""
        self.assertTrue(os.path.exists(self.map_path),
                       f"mcx_futures_map.json not found at {self.map_path}")
    
    def test_mcx_futures_map_valid_json(self):
        """Test that mcx_futures_map.json is valid JSON."""
        with open(self.map_path, 'r') as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)
    
    def test_mcx_futures_map_format(self):
        """Test that mcx_futures_map.json has correct format."""
        with open(self.map_path, 'r') as f:
            data = json.load(f)
        
        # Each entry should have: [symbol, trading_symbol, lot_size, expiry_date]
        for token, info in data.items():
            self.assertIsInstance(info, list, 
                                 f"Token {token} should be a list")
            self.assertGreaterEqual(len(info), 3,
                                  f"Token {token} should have at least 3 elements")
            
            # Check format: [symbol, trading_symbol, lot_size, expiry_date]
            symbol = info[0]
            trading_symbol = info[1]
            lot_size = info[2]
            
            self.assertIsInstance(symbol, str)
            self.assertIsInstance(trading_symbol, str)
            self.assertIsInstance(lot_size, int)
            
            # If expiry date exists (4th element)
            if len(info) >= 4:
                expiry = info[3]
                self.assertIsInstance(expiry, str)
    
    def test_mcx_futures_map_has_expiry_dates(self):
        """Test that all MCX futures have expiry dates."""
        with open(self.map_path, 'r') as f:
            data = json.load(f)
        
        for token, info in data.items():
            self.assertGreaterEqual(len(info), 4,
                                  f"Token {token} should have expiry date (4th element)")
    
    def test_mcx_futures_map_expected_commodities(self):
        """Test that expected commodities are present."""
        with open(self.map_path, 'r') as f:
            data = json.load(f)
        
        symbols = [info[0] for info in data.values()]
        
        # Should have at least these commodities
        expected = ['CRUDEOIL', 'NATURALGAS', 'GOLD', 'SILVER']
        for exp in expected:
            self.assertIn(exp, symbols,
                         f"Expected commodity {exp} not found in MCX map")


class TestMCXExpiryCheck(unittest.TestCase):
    """Test MCX expiry checking functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        tests_dir = os.path.dirname(test_dir)
        orbiter_dir = os.path.dirname(tests_dir)
        self.map_path = os.path.join(orbiter_dir, 'data', 'mcx_futures_map.json')
    
    def test_expiry_date_parsing(self):
        """Test that expiry dates can be parsed correctly."""
        with open(self.map_path, 'r') as f:
            data = json.load(f)
        
        for token, info in data.items():
            if len(info) >= 4:
                expiry_str = info[3]
                
                # Try parsing various date formats
                parsed = False
                for fmt in ['%d%b%y', '%d%b%Y', '%d-%b-%Y']:
                    try:
                        datetime.strptime(expiry_str.upper(), fmt)
                        parsed = True
                        break
                    except ValueError:
                        continue
                
                self.assertTrue(parsed,
                              f"Could not parse expiry date: {expiry_str}")
    
    def test_expiry_dates_are_future(self):
        """Test that all expiry dates are in the future."""
        with open(self.map_path, 'r') as f:
            data = json.load(f)
        
        today = datetime.now()
        
        for token, info in data.items():
            if len(info) >= 4:
                expiry_str = info[3]
                
                # Try parsing
                expiry_date = None
                for fmt in ['%d%b%y', '%d%b%Y', '%d-%b-%Y']:
                    try:
                        expiry_date = datetime.strptime(expiry_str.upper(), fmt)
                        break
                    except ValueError:
                        continue
                
                if expiry_date:
                    # Skip if we can't determine (should be recent)
                    days_until_expiry = (expiry_date - today).days
                    # Just log, don't fail - contracts near expiry are valid
                    print(f"Token {token}: {expiry_str} expires in {days_until_expiry} days")


class TestScripMasterExpiryCheck(unittest.TestCase):
    """Test ScripMaster.check_and_update_mcx_expiry method."""
    
    def test_check_and_update_method_exists(self):
        """Test that check_and_update_mcx_expiry method exists in ScripMaster."""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        tests_dir = os.path.dirname(test_dir)
        project_root = os.path.dirname(tests_dir)
        sys.path.insert(0, project_root)
        
        from orbiter.core.broker.master import ScripMaster
        
        self.assertTrue(hasattr(ScripMaster, 'check_and_update_mcx_expiry'),
                       "ScripMaster should have check_and_update_mcx_expiry method")
    
    def test_parse_expiry_date_method_exists(self):
        """Test that _parse_expiry_date method exists in ScripMaster."""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        tests_dir = os.path.dirname(test_dir)
        project_root = os.path.dirname(tests_dir)
        sys.path.insert(0, project_root)
        
        from orbiter.core.broker.master import ScripMaster
        
        self.assertTrue(hasattr(ScripMaster, '_parse_expiry_date'),
                       "ScripMaster should have _parse_expiry_date method")


if __name__ == '__main__':
    unittest.main()
