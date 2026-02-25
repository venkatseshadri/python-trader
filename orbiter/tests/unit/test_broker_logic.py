import pytest
import datetime
from unittest.mock import MagicMock
from orbiter.core.broker.resolver import ContractResolver
from orbiter.core.broker.margin import MarginCalculator

def test_is_last_thursday():
    resolver = ContractResolver(MagicMock())
    # 26 Feb 2026 is the last Thursday
    assert resolver._is_last_thursday(datetime.date(2026, 2, 26)) is True
    # 19 Feb 2026 is NOT the last Thursday
    assert resolver._is_last_thursday(datetime.date(2026, 2, 19)) is False

def test_contract_resolution():
    mock_master = MagicMock()
    # Mock some option rows for Nifty
    mock_master.DERIVATIVE_OPTIONS = [
        {'symbol': 'NIFTY', 'instrument': 'OPTSTK', 'expiry': '2026-02-26', 'strike': 25000.0, 'option_type': 'PE', 'tradingsymbol': 'NIFTY26FEB25000PE', 'lot_size': 50, 'exchange': 'NFO'},
        {'symbol': 'NIFTY', 'instrument': 'OPTSTK', 'expiry': '2026-02-26', 'strike': 24800.0, 'option_type': 'PE', 'tradingsymbol': 'NIFTY26FEB24800PE', 'lot_size': 50, 'exchange': 'NFO'},
        {'symbol': 'NIFTY', 'instrument': 'OPTSTK', 'expiry': '2026-02-26', 'strike': 25100.0, 'option_type': 'PE', 'tradingsymbol': 'NIFTY26FEB25100PE', 'lot_size': 50, 'exchange': 'NFO'}
    ]
    mock_master.DERIVATIVE_LOADED = True
    # Helper to return the date object directly for mocked strings
    mock_master._parse_expiry_date.side_effect = lambda x: datetime.datetime.strptime(x, "%Y-%m-%d").date()

    resolver = ContractResolver(mock_master)
    
    # Test Bullish Spread (PUT) at LTP 25010
    # Expected: ATM 25000, Hedge (4 steps of 100/200? wait, step calculation check)
    # The strikes are [24800, 25000, 25100]. Step = 100 (diff between 25100 and 25000)
    # LTP 25010 -> closest is 25000 (ATM).
    # Step = 100. Hedge steps 2 (for simplicity in mock) -> 25000 - (2*100) = 24800.
    
    result = resolver.get_credit_spread_contracts(
        symbol='NIFTY', ltp=25010.0, side='PUT', hedge_steps=2, 
        expiry_type='monthly', instrument='OPTSTK'
    )
    
    assert result['ok'] is True
    assert result['atm_strike'] == 25000.0
    assert result['hedge_strike'] == 24800.0
    assert result['atm_symbol'] == 'NIFTY26FEB25000PE'

def test_margin_calculation_payload():
    mock_master = MagicMock()
    mock_master.DERIVATIVE_OPTIONS = [
        {'tradingsymbol': 'ATM_PE', 'symbol': 'NIFTY', 'expiry': '2026-02-26', 'strike': 25000.0, 'option_type': 'PE', 'instrument': 'OPTSTK'},
        {'tradingsymbol': 'HDG_PE', 'symbol': 'NIFTY', 'expiry': '2026-02-26', 'strike': 24800.0, 'option_type': 'PE', 'instrument': 'OPTSTK'}
    ]
    
    calc = MarginCalculator(mock_master)
    mock_api = MagicMock()
    mock_api.span_calculator.return_value = {
        'stat': 'Ok', 'span': '15000.0', 'expo': '5000.0', 'total_margin': '20000.0'
    }
    
    spread = {'atm_symbol': 'ATM_PE', 'hedge_symbol': 'HDG_PE', 'lot_size': 50}
    
    result = calc.calculate_span_for_spread(spread, mock_api, 'USER123')
    
    assert result['ok'] is True
    assert result['total_margin'] == 20000.0
    # Verify the structure of the call to Shoonya API
    mock_api.span_calculator.assert_called_once()
    pos_list = mock_api.span_calculator.call_args[0][1]
    assert len(pos_list) == 2
    assert pos_list[0]['optt'] == 'PE'
    assert pos_list[1]['optt'] == 'PE'
