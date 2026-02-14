import pytest
import json
import os
from filters.entry.f1_orb import orb_filter

def load_scenarios():
    path = os.path.join(os.path.dirname(__file__), '../data/scenario_data.json')
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
        return data['scenarios']

SCENARIOS = load_scenarios()

@pytest.mark.parametrize("scenario", [s for s in SCENARIOS if s['id'] == "SCENARIO_001_BULLISH_ORB"])
def test_orb_breakout_logic(scenario, mocker):
    inputs = scenario['inputs']
    expected = scenario['expected_behavior']
    
    # Prepare dummy candle data for calculate_orb_range fallback
    # In a real scenario, we'd provide the 15 candles, but here we mock the range for pure filter testing
    mocker.patch('filters.entry.f1_orb.calculate_orb_range', return_value=(
        inputs['orb_15m_high'], 
        inputs['orb_15m_low'], 
        inputs['breakout_candle_1m']['open'] # Using breakout open as proxy for day open
    ))
    
    # Tick data representing the breakout
    tick_data = {
        'lp': str(inputs['breakout_candle_1m']['close']),
        'o': str(inputs['breakout_candle_1m']['open']),
        'tk': '26000'
    }
    
    result = orb_filter(tick_data, ret=[], token='26000')
    
    assert result['orb_high'] == inputs['orb_15m_high']
    assert result['orb_low'] == inputs['orb_15m_low']
    
    if expected['is_breakout']:
        assert result['score'] > 0
        assert tick_data['lp'] > str(result['orb_high'])
