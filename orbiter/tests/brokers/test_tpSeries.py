"""
Test BFO TPSeries data retrieval from Shoonya API.

This validates that historical candle data can be fetched for:
- SENSEX Future (BFO|825565)
- SENSEX Option (BFO|863172)
"""
import pytest
import os
import sys

# Get project root
file_path = os.path.abspath(__file__)
tests_dir = os.path.dirname(file_path)
orbiter_dir = os.path.dirname(tests_dir)
project_root = os.path.dirname(orbiter_dir)
sys.path.insert(0, project_root)

from orbiter.core.broker import BrokerClient


@pytest.fixture(scope="module")
def client():
    """Create BrokerClient and login."""
    # Let BrokerClient find credentials - it will use default paths
    client = BrokerClient(project_root, segment_name='bfo')
    
    success = client.login()
    if not success:
        pytest.skip("Broker login failed")
    
    yield client
    client.close()


def _get_last_business_day():
    """Get the last business day for testing."""
    import pytz
    import datetime
    
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(tz=ist)
    
    # If before 10 AM, use yesterday
    if now_ist.hour < 10:
        last_bus_day = now_ist - datetime.timedelta(days=1)
    else:
        last_bus_day = now_ist
    
    # Skip weekends
    while last_bus_day.weekday() >= 5:
        last_bus_day = last_bus_day - datetime.timedelta(days=1)
    
    return last_bus_day


def test_bfo_tpseries_sensex_future(client):
    """Test: Verify SENSEX Future (BFO|825565) historical data works."""
    import pytz
    import datetime
    
    last_bus_day = _get_last_business_day()
    
    # 10:00 AM to 11:00 AM
    start_dt = last_bus_day.replace(hour=10, minute=0, second=0, microsecond=0)
    end_dt = last_bus_day.replace(hour=11, minute=0, second=0, microsecond=0)

    # 825565 is SENSEX26MARFUT (March expiry)
    ret = client.api.get_time_price_series(
        exchange='BFO',
        token='825565',
        starttime=start_dt.timestamp(),
        endtime=end_dt.timestamp(),
        interval=5
    )
    
    print(f"\n[BFO Future] Token: 825565 (SENSEX26MARFUT)")
    print(f"  Request: {start_dt} to {end_dt}")
    print(f"  Response type: {type(ret)}")
    
    if isinstance(ret, list):
        print(f"  Candles returned: {len(ret)}")
        if ret:
            print(f"  First candle keys: {list(ret[0].keys())}")
            print(f"  Sample: {ret[0]}")
    else:
        print(f"  Response: {ret}")
    
    # Assertions
    assert ret is not None, "Response should not be None"
    assert isinstance(ret, list), f"Expected list, got {type(ret)}"
    assert len(ret) > 0, "Should return at least one candle"
    assert 'intc' in ret[0], "Candle should have close price (intc)"


def test_bfo_tpseries_sensex_option(client):
    """Test: Verify SENSEX Option (BFO) historical data works.
    
    IMPORTANT: Token 845683 (Mar 12 PE 79000) expires weekly!
    Update this token when the current weekly contract expires:
    - Check bfo_symbols.json for the next week's ATM option token
    - Look for BSXOPT with expiry = next Thursday's date
    - Use ATM strike (closest to current SENSEX level ~79000)
    
    Example: When Mar 12 contract expires, update to Mar 19 ATM token.
    """
    last_bus_day = _get_last_business_day()
    
    # Use yesterday's full day window when market was open
    # March 5 is expiry day - options may have stopped trading
    start_dt = last_bus_day.replace(hour=9, minute=15, second=0, microsecond=0)
    end_dt = last_bus_day.replace(hour=15, minute=30, second=0, microsecond=0)

    # 845683 is SENSEX Mar 12 PE 79000 (ATM option - most liquid)
    token = '845683' 
    
    ret = client.api.get_time_price_series(
        exchange='BFO',
        token=token,
        starttime=start_dt.timestamp(),
        endtime=end_dt.timestamp(),
        interval=15
    )
    
    print(f"\n[BFO Option] Token: {token} (Mar 12 PE 79000 - ATM)")
    print(f"  Request: {start_dt} to {end_dt}")
    print(f"  Response type: {type(ret)}")
    
    if isinstance(ret, list):
        print(f"  Candles returned: {len(ret)}")
        if ret:
            print(f"  First candle keys: {list(ret[0].keys())}")
            print(f"  Sample: {ret[0]}")
    else:
        print(f"  Response: {ret}")
    
    # Should return data for ATM option
    assert ret is not None
    assert isinstance(ret, list)
    assert len(ret) > 0
    assert 'intc' in ret[0]
    
    assert ret is not None
    assert isinstance(ret, list)
    assert len(ret) > 0
    assert 'intc' in ret[0]


if __name__ == '__main__':
    pytest.main([__file__, '-s'])
