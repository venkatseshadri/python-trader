#!/usr/bin/env python3
"""
Example tests using captured data fixtures.

This demonstrates how to use the captured data fixtures.
When captured data exists, tests use real data.
When not available, tests use fallback mock data.

Run:
    # First capture (requires broker login):
    python3 capture_test_data.py
    
    # Then run tests:
    python3 -m pytest test_captured_data_example.py -v
"""

import pytest
import sys
import os

# Ensure project root in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


class TestCapturedDataFixtures:
    """Tests demonstrating captured data usage."""
    
    def test_nse_scrip_data_available(self, scrip_nse):
        """Test that NSE scrip data is available (captured or mock)."""
        # Should have at least one token
        assert len(scrip_nse) > 0, "NSE scrip data should not be empty"
        
        # Check structure of first item
        first_token = next(iter(scrip_nse.keys()))
        first_item = scrip_nse[first_token]
        
        assert 'token' in first_item
        assert 'symbol' in first_item
        assert 'exchange' in first_item
        
        print(f"✅ NSE scrip data: {len(scrip_nse)} tokens loaded")
    
    def test_nfo_scrip_data_available(self, scrip_nfo):
        """Test that NFO scrip data is available."""
        assert len(scrip_nfo) > 0, "NFO scrip data should not be empty"
        print(f"✅ NFO scrip data: {len(scrip_nfo)} options loaded")
    
    def test_margins_data_available(self, captured_margins):
        """Test that margin data is available."""
        # Check for expected keys
        assert 'available_margin' in captured_margins or 'cash' in captured_margins
        print(f"✅ Margin data: {captured_margins}")
    
    def test_candles_data_available(self, captured_candles):
        """Test that candle data is available (if captured)."""
        # Candles might be empty if not captured
        print(f"✅ Candle data: {len(captured_candles)} symbol sets")
    
    def test_with_mock_fallback(self, mock_scrip_data):
        """Test that strict mock data always works."""
        # This fixture provides hard-coded mocks
        assert '12345' in mock_scrip_data
        assert mock_scrip_data['12345']['symbol'] == 'RECLTD'
        print("✅ Strict mock data fallback works")


class TestBrokerConnectionMock:
    """Tests using mocked broker connection with captured data."""
    
    def test_simulate_broker_with_captured_scrip(self, scrip_nse, scrip_nfo):
        """Simulate using captured scrip data in broker operations."""
        # Build a mock SYMBOLDICT structure
        SYMBOLDICT = {}
        
        for token, info in list(scrip_nse.items())[:10]:
            key = f"NSE|{token}"
            SYMBOLDICT[key] = {
                'symbol': info.get('symbol', ''),
                'token': token,
                'ltp': 100.0,  # Mock LTP
                'exchange': 'NSE',
            }
        
        assert len(SYMBOLDICT) > 0
        print(f"✅ Built SYMBOLDICT with {len(SYMBOLDICT)} entries from captured data")
    
    def test_simulate_margin_check(self, captured_margins):
        """Simulate margin check with captured data."""
        available = captured_margins.get('available_margin', 0)
        
        # Simple logic: can we place a 10000 margin trade?
        can_trade = available >= 10000
        
        assert can_trade is not None
        print(f"✅ Margin check: available={available}, can_trade={can_trade}")


class TestLiveBrokerRequired:
    """Tests that REQUIRE live broker - cannot use captured data."""
    
    @pytest.mark.live
    @pytest.mark.skip(reason="Requires live broker - run capture_test_data.py first")
    def test_actual_login(self):
        """This test REQUIRES actual broker login."""
        from orbiter.core.broker.connection import ConnectionManager
        
        conn = ConnectionManager()
        result = conn.login()
        
        assert result is True, "Login should succeed with valid credentials"
        conn.close()
    
    @pytest.mark.live
    @pytest.mark.skip(reason="Requires live broker - compute actual margins")
    def test_actual_margin_calculation(self):
        """This test requires computing actual margins."""
        # This would call the actual broker API
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])