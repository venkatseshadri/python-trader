import pytest
from unittest.mock import MagicMock
from datetime import datetime
from orbiter.core.engine.runtime.syncer import Syncer

def test_sync_active_positions_payload_preparation():
    # 1. Setup Mock Callback
    mock_update_callback = MagicMock()
    syncer = Syncer(mock_update_callback)

    # 2. Setup Mock State
    mock_state = MagicMock()
    mock_state.client.SYMBOLDICT = {
        '12345': {'ltp': 25050.0, 'current_net_premium': 5.0}
    }
    mock_state.client.span_cache = {}
    mock_state.config = {'OPTION_EXPIRY': 'monthly', 'OPTION_INSTRUMENT': 'OPTSTK', 'HEDGE_STEPS': 4}
    
    # Simulate an active position
    entry_time = datetime(2026, 2, 14, 10, 0)
    mock_state.active_positions = {
        '12345': {
            'symbol': 'NIFTY 50',
            'company_name': 'NIFTY',
            'entry_price': 25000.0,
            'entry_time': entry_time,
            'entry_net_premium': 10.0,
            'atm_premium_entry': 20.0,
            'lot_size': 50,
            'strategy': 'PUT_CREDIT_SPREAD',
            'atm_symbol': 'NIFTY26FEB25000PE',
            'hedge_symbol': 'NIFTY26FEB24800PE',
            'expiry': '26-FEB-2026'
        }
    }

    # 3. Execute
    syncer.sync_active_positions_to_sheets(mock_state)

    # 4. Verify Payload
    mock_update_callback.assert_called_once()
    payload = mock_update_callback.call_args[0][0]
    
    assert len(payload) == 1
    p = payload[0]
    assert p['symbol'] == 'NIFTY 50'
    assert p['ltp'] == 25050.0
    # PnL logic check: (Entry Net 10 - Current Net 5) * Lot 50 = 250
    assert p['pnl_rs'] == 250.0
    # PnL % check: (10 - 5) / 20 * 100 = 25%
    assert p['pnl_pct'] == 25.0
    assert "2026-02-14 10:00:00 IST" in p['entry_time']
