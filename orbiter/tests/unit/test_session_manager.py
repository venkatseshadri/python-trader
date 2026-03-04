#!/usr/bin/env python3
"""
Tests for SessionManager - strategy loading and resolution.

This tests the critical path of loading strategy configurations
from the strategy bundle.
"""
import os
import sys
import unittest

# Get project root - this test is in orbiter/tests/unit/
test_dir = os.path.dirname(os.path.abspath(__file__))  # tests/unit
tests_dir = os.path.dirname(test_dir)  # tests
orbiter_dir = os.path.dirname(tests_dir)  # orbiter
project_root = os.path.dirname(orbiter_dir)  # python (parent of orbiter)
sys.path.insert(0, project_root)

from orbiter.utils.schema_manager import SchemaManager


class TestSessionManager(unittest.TestCase):
    """Test SessionManager strategy loading."""
    
    def setUp(self):
        """Reset SchemaManager singleton before each test."""
        SchemaManager._instance = None
        os.environ['ORBITER_STRATEGY'] = 'mcx_trend_follower'
    
    def tearDown(self):
        """Clean up after each test."""
        SchemaManager._instance = None
        if 'ORBITER_STRATEGY' in os.environ:
            del os.environ['ORBITER_STRATEGY']
    
    def test_schema_loads_correctly(self):
        """Test that SchemaManager loads schema.json correctly."""
        schema = SchemaManager.get_instance(project_root)
        
        # Check key schema sections exist
        self.assertIn('rule_schema', schema._schema)
        self.assertIn('strategy_schema', schema._schema)
        
        # Check strategy_schema keys
        strategy_schema = schema.get_key('strategy_schema')
        self.assertEqual(strategy_schema.get('files_key'), 'files')
        self.assertEqual(strategy_schema.get('rules_file_key'), 'rules_file')
    
    def test_strategy_schema_keys(self):
        """Test strategy schema returns correct keys."""
        schema = SchemaManager.get_instance(project_root)
        
        # Test with key_name
        files_key = schema.get_key('strategy_schema', 'files_key')
        self.assertEqual(files_key, 'files')
        
        rules_key = schema.get_key('strategy_schema', 'rules_file_key')
        self.assertEqual(rules_key, 'rules_file')
    
    def test_rule_schema_keys(self):
        """Test rule schema returns correct keys."""
        schema = SchemaManager.get_instance(project_root)
        
        rules_key = schema.get_key('rule_schema', 'rules_key')
        self.assertEqual(rules_key, 'strategies')
        
        conditions_key = schema.get_key('rule_schema', 'conditions_key')
        self.assertEqual(conditions_key, 'market_signals')


class TestSchemaLoading(unittest.TestCase):
    """Test schema loading from config files."""
    
    def setUp(self):
        """Reset SchemaManager singleton before each test."""
        SchemaManager._instance = None
    
    def tearDown(self):
        """Clean up after each test."""
        SchemaManager._instance = None
    
    def test_schema_file_exists(self):
        """Test that schema.json exists in config directory."""
        schema_path = os.path.join(orbiter_dir, 'config', 'schema.json')
        self.assertTrue(os.path.exists(schema_path), 
                       f"schema.json not found at {schema_path}")
    
    def test_schema_has_required_keys(self):
        """Test that schema.json has all required sections."""
        schema = SchemaManager.get_instance(project_root)
        
        required_sections = [
            'rule_schema',
            'strategy_schema', 
            'session_schema',
            'global_schema'
        ]
        
        for section in required_sections:
            self.assertIn(section, schema._schema, 
                         f"Missing required section: {section}")


class TestStrategyBundle(unittest.TestCase):
    """Test strategy bundle loading."""
    
    def setUp(self):
        """Reset SchemaManager singleton before each test."""
        SchemaManager._instance = None
        os.environ['ORBITER_STRATEGY'] = 'mcx_trend_follower'
    
    def tearDown(self):
        """Clean up after each test."""
        SchemaManager._instance = None
        if 'ORBITER_STRATEGY' in os.environ:
            del os.environ['ORBITER_STRATEGY']
    
    def test_mcx_strategy_bundle_loads(self):
        """Test that MCX strategy bundle loads correctly."""
        from orbiter.core.engine.session.session_manager import SessionManager
        
        session = SessionManager(project_root, paper_trade=True)
        
        # Check strategy bundle is loaded
        self.assertIsNotNone(session.strategy_bundle)
        self.assertIn('name', session.strategy_bundle)
        self.assertIn('files', session.strategy_bundle)
        
        # Check files section
        files = session.strategy_bundle.get('files', {})
        self.assertIn('rules_file', files)
        self.assertIn('filters_file', files)
        self.assertIn('instruments_file', files)
    
    def test_get_active_rules_file(self):
        """Test that get_active_rules_file returns correct path."""
        from orbiter.core.engine.session.session_manager import SessionManager
        
        session = SessionManager(project_root, paper_trade=True)
        
        rules_file = session.get_active_rules_file()
        
        # Should return a path like "orbiter/strategies/mcx_trend_follower/rules.json"
        self.assertIsNotNone(rules_file)
        self.assertIn('rules.json', rules_file)
        self.assertIn('mcx_trend_follower', rules_file)
    
    def test_get_active_segment_name(self):
        """Test that get_active_segment_name returns correct segment."""
        from orbiter.core.engine.session.session_manager import SessionManager
        
        session = SessionManager(project_root, paper_trade=True)
        
        segment = session.get_active_segment_name()
        
        # MCX strategy should have 'mcx' segment
        self.assertEqual(segment, 'mcx')
    
    def test_get_active_universe(self):
        """Test that get_active_universe returns instruments list."""
        from orbiter.core.engine.session.session_manager import SessionManager
        
        session = SessionManager(project_root, paper_trade=True)
        
        universe = session.get_active_universe()
        
        # Should be a list of instruments
        self.assertIsInstance(universe, list)
        if universe:  # If not empty
            self.assertIn('symbol', universe[0])


if __name__ == '__main__':
    unittest.main()
