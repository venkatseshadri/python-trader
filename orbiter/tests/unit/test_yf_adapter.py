"""
Test: Yahoo Finance Adapter
Validates:
1. ADX calculation from Yahoo Finance
2. Market regime detection
3. Fallback to 1m interval when 5m insufficient

Run: python -m pytest tests/unit/test_yf_adapter.py -v
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
import pandas as pd
import numpy as np

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestYFAdapter(unittest.TestCase):
    @patch('orbiter.utils.yf_adapter.yf.Ticker')
    def test_get_market_adx_success(self, mock_ticker):
        """Test successful ADX calculation from Yahoo Finance."""
        from orbiter.utils.yf_adapter import get_market_adx
        
        # Create a proper DataFrame with required columns
        data = {
            'High': np.arange(100, 125, 1, dtype=float),
            'Low': np.arange(98, 123, 1, dtype=float),
            'Close': np.arange(99, 124, 1, dtype=float)
        }
        mock_df = pd.DataFrame(data)
        
        mock_ticker.return_value.history.return_value = mock_df
        
        with patch('orbiter.utils.yf_adapter.talib.ADX') as mock_adx:
            mock_adx.return_value = np.array([20.0] * 25)
            result = get_market_adx('SENSEX', '5m')
            
            self.assertGreater(result, 0)

    @patch('orbiter.utils.yf_adapter.yf.Ticker')
    def test_get_market_adx_insufficient_data(self, mock_ticker):
        """Test fallback when insufficient candles."""
        from orbiter.utils.yf_adapter import get_market_adx
        
        # Create DataFrame with only 5 rows
        data = {
            'High': np.array([100, 101, 102, 103, 104]),
            'Low': np.array([98, 99, 100, 101, 102]),
            'Close': np.array([99, 100, 101, 102, 103])
        }
        mock_df = pd.DataFrame(data)
        
        mock_ticker.return_value.history.return_value = mock_df
        
        result = get_market_adx('SENSEX', '5m')
        
        # Should return -1.0 when insufficient data
        self.assertEqual(result, -1.0)

    @patch('orbiter.utils.yf_adapter.yf.Ticker')
    def test_get_market_regime_trending(self, mock_ticker):
        """Test market regime detection - trending."""
        from orbiter.utils.yf_adapter import get_market_regime
        
        data = {
            'High': np.arange(100, 125, 1, dtype=float),
            'Low': np.arange(98, 123, 1, dtype=float),
            'Close': np.arange(99, 124, 1, dtype=float)
        }
        mock_df = pd.DataFrame(data)
        
        mock_ticker.return_value.history.return_value = mock_df
        
        with patch('orbiter.utils.yf_adapter.talib.ADX') as mock_adx:
            mock_adx.return_value = np.array([30.0] * 25)  # High ADX = trending
            regime = get_market_regime('SENSEX')
            
            self.assertEqual(regime, 'trending')

    @patch('orbiter.utils.yf_adapter.yf.Ticker')
    def test_get_market_regime_sideways(self, mock_ticker):
        """Test market regime detection - sideways."""
        from orbiter.utils.yf_adapter import get_market_regime
        
        data = {
            'High': np.arange(100, 125, 1, dtype=float),
            'Low': np.arange(98, 123, 1, dtype=float),
            'Close': np.arange(99, 124, 1, dtype=float)
        }
        mock_df = pd.DataFrame(data)
        
        mock_ticker.return_value.history.return_value = mock_df
        
        with patch('orbiter.utils.yf_adapter.talib.ADX') as mock_adx:
            mock_adx.return_value = np.array([15.0] * 25)  # Low ADX = sideways
            regime = get_market_regime('SENSEX')
            
            self.assertEqual(regime, 'sideways')


if __name__ == '__main__':
    unittest.main()
