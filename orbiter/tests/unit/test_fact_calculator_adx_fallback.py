"""
Test: Fact Calculator ADX Fallback
Validates that:
1. YF ADX fallback works when broker candles are insufficient
2. ADX is cached and reused within TTL window

Run: python -m pytest tests/unit/test_fact_calculator_adx_fallback.py -v
"""
import unittest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import numpy as np

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from orbiter.core.engine.rule.fact_calculator import FactCalculator, _yf_adx_cache
from orbiter.utils.data_manager import DataManager
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager


class TestFactCalculatorADXFallback(unittest.TestCase):
    """Test YF ADX fallback when broker candles are insufficient."""

    @classmethod
    def setUpClass(cls):
        ConstantsManager._instance = None
        SchemaManager._instance = None
        cls.project_root = project_root
        cls.facts_path = DataManager.get_manifest_path(cls.project_root, 'mandatory_files', 'fact_definitions')
        cls.fact_definitions = DataManager.load_json(cls.facts_path)

    def setUp(self):
        global _yf_adx_cache
        _yf_adx_cache = {'value': None, 'timestamp': 0}

    def test_adx_fallback_when_insufficient_candles(self):
        """Verify YF ADX is used when broker candles < 20."""
        calc = FactCalculator(self.project_root, self.fact_definitions)
        
        standardized = {
            'close': np.array([100, 101, 102]),  # Only 3 candles - insufficient
            'high': np.array([102, 103, 104]),
            'low': np.array([99, 100, 101]),
            'open': np.array([99, 101, 102]),
            'volume': np.array([1000, 1100, 1200]),
        }

        with patch('orbiter.core.engine.rule.fact_calculator.get_market_adx') as mock_adx:
            mock_adx.return_value = 28.5
            
            facts = calc.calculate_technical_facts(standardized, token='TEST_TOKEN')
            
            self.assertIn('market_adx', facts)
            self.assertEqual(facts['market_adx'], 28.5)
            mock_adx.assert_called_once()

    def test_adx_not_used_when_sufficient_candles(self):
        """Verify broker ADX is used when candles >= 20."""
        calc = FactCalculator(self.project_root, self.fact_definitions)
        
        close = np.arange(100, 130, 1)  # 30 candles
        standardized = {
            'close': close,
            'high': close + 2,
            'low': close - 2,
            'open': close - 1,
            'volume': np.ones(30) * 1000,
        }

        with patch('orbiter.core.engine.rule.fact_calculator.get_market_adx') as mock_adx:
            facts = calc.calculate_technical_facts(standardized, token='TEST_TOKEN')
            
            # Should have broker-calculated ADX (not from fallback)
            self.assertIn('market_adx', facts)
            # mock_adx should NOT be called when sufficient candles
            mock_adx.assert_not_called()

    def test_adx_caching(self):
        """Verify ADX is cached and reused within TTL."""
        calc = FactCalculator(self.project_root, self.fact_definitions)
        
        standardized = {
            'close': np.array([100, 101, 102]),
            'high': np.array([102, 103, 104]),
            'low': np.array([99, 100, 101]),
            'open': np.array([99, 101, 102]),
            'volume': np.array([1000, 1100, 1200]),
        }

        import time
        with patch('orbiter.core.engine.rule.fact_calculator.get_market_adx') as mock_adx:
            mock_adx.return_value = 25.0
            
            # First call - should fetch
            facts1 = calc.calculate_technical_facts(standardized, token='TEST_TOKEN')
            self.assertEqual(mock_adx.call_count, 1)
            
            # Second call - should use cache (simulate same timestamp)
            facts2 = calc.calculate_technical_facts(standardized, token='TEST_TOKEN')
            self.assertEqual(mock_adx.call_count, 1)  # Still 1, not 2


if __name__ == '__main__':
    unittest.main()
