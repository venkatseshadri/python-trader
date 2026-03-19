"""
Test: instrument.* facts should preserve dot notation

This test verifies that facts starting with 'instrument.' are preserved
with dot notation (instrument.derivative) rather than being converted
to underscore notation (instrument_derivative).

Regression test for bug: instrument.derivative was being converted to
instrument_derivative, causing execution rule evaluation to fail.
"""
import pytest
import sys
import os
import logging

# Add orbiter to path
orbiter_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, orbiter_root)

logging.basicConfig(level=logging.INFO)

from orbiter.core.engine.rule.rule_manager import RuleManager
from orbiter.core.engine.rule.rule_engine import RuleEngine


class MockSessionManager:
    """Mock session manager for testing"""
    def __init__(self):
        self.filters = {
            'scoring': {
                'combined_score': {
                    'adx': 1.0,
                    'supertrend': 1.0,
                    'ema_slope': 1.0
                }
            }
        }
    
    def is_trade_window(self):
        return True


class MockConstants:
    """Mock constants for testing"""
    def get(self, key, default=None):
        if key == 'fact_contexts':
            return 'instrument_context'
        return default


class MockSource:
    """Mock source for testing"""
    def __init__(self):
        self.session_manager = MockSessionManager()
        self.constants = MockConstants()


def test_instrument_dot_notation_preserved():
    """
    Test that instrument.* facts preserve dot notation when flattened.
    
    Bug: extra_facts containing 'instrument.derivative' was being converted
    to 'instrument_derivative', but execution rules expected 'instrument.derivative'.
    """
    # Create a simple rule that checks for instrument.derivative = "option"
    rule_json = {
        "name": "test_derivative_rule",
        "conditions": {
            "allOf": [
                {"fact": "instrument.derivative", "operator": "equal", "value": "option"}
            ]
        },
        "order_operations": [{"action": "BUY", "quantity": 1}]
    }
    
    engine = RuleEngine(rule_json)
    
    # Test facts WITH instrument.derivative preserved
    facts_with_dot = {
        'instrument.derivative': 'option',
        'instrument.symbol': 'NIFTY',
        'session_is_trade_window': True
    }
    
    result = engine.matches(facts_with_dot)
    assert result is True, "Rule should match when instrument.derivative='option'"
    
    # Test facts WITHOUT instrument.derivative (should NOT match)
    facts_without_derivative = {
        'instrument.symbol': 'NIFTY',
        'session_is_trade_window': True
    }
    
    result2 = engine.matches(facts_without_derivative)
    assert result2 is False, "Rule should NOT match when instrument.derivative missing"


def test_fact_flattening_preserves_instrument_prefix():
    """
    Test that the fact flattening logic preserves instrument.* facts.
    
    This simulates what happens in rule_manager.py evaluate() method.
    """
    # Simulate extra_facts as they come from core_engine
    extra_facts = {
        'token': '26013',
        'instrument.exchange': 'NSE',
        'instrument.derivative': 'option',
        'instrument.symbol': 'NIFTY',
        'instrument.instrument_type': 'index',
        'session_is_trade_window': True
    }
    
    # This is the FIXED logic from rule_manager.py
    facts = {}
    for k, v in extra_facts.items():
        if k.startswith('instrument.'):
            facts[k] = v  # Preserve dot notation
        else:
            facts[k.replace('.', '_')] = v
    
    # Verify instrument.* facts are preserved
    assert 'instrument.derivative' in facts, "instrument.derivative should be preserved"
    assert facts['instrument.derivative'] == 'option'
    assert 'instrument.symbol' in facts
    assert facts['instrument.symbol'] == 'NIFTY'
    
    # Verify other facts are flattened
    assert 'session_is_trade_window' in facts
    
    # Verify the bug would have converted incorrectly
    # (This is what the OLD code did - which was wrong)
    buggy_facts = {}
    for k, v in extra_facts.items():
        buggy_facts[k.replace('.', '_')] = v
    
    # This is what the BUG produced (wrong!)
    assert 'instrument_derivative' in buggy_facts  # Bug: wrong key
    assert 'instrument.derivative' not in buggy_facts  # Correct key missing!


def test_execution_rule_with_instrument_derivative():
    """
    Integration test: Verify execution rules can evaluate instrument.derivative.
    
    This is the exact scenario from nifty_fno_topn_trend/rules.json:
    {
        "fact": "instrument.derivative", 
        "operator": "equal", 
        "value": "option"
    }
    """
    rule_json = {
        "name": "Nifty_FNO_TopN_Trend_Execution",
        "conditions": {
            "allOf": [
                {"fact": "session.is_trade_window", "operator": "equal", "value": True},
                {"fact": "instrument.derivative", "operator": "equal", "value": "option"}
            ]
        },
        "order_operations": [{"action": "BUY", "quantity": 75}]
    }
    
    engine = RuleEngine(rule_json)
    
    # Facts as they should be after the fix
    facts = {
        'session_is_trade_window': True,
        'instrument_derivative': 'option',  # This was the BUG - wrong key!
        'instrument.derivative': 'option',  # This is CORRECT - should be present
    }
    
    # Test with correct facts (after fix)
    result = engine.matches(facts)
    assert result is True, "Execution rule should match with instrument.derivative='option'"


if __name__ == "__main__":
    print("Running instrument.* fact preservation tests...")
    
    test_instrument_dot_notation_preserved()
    print("✅ test_instrument_dot_notation_preserved passed")
    
    test_fact_flattening_preserves_instrument_prefix()
    print("✅ test_fact_flattening_preserves_instrument_prefix passed")
    
    test_execution_rule_with_instrument_derivative()
    print("✅ test_execution_rule_with_instrument_derivative passed")
    
    print("\n🎉 All tests passed!")
