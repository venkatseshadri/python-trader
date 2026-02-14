import pytest
from unittest.mock import MagicMock, patch
from core.engine.executor import Executor
from core.engine.state import OrbiterState

def test_executor_logging_on_signal():
    # 1. Mock Callbacks
    mock_log_buy = MagicMock()
    mock_log_close = MagicMock()
    
    executor = Executor(
        log_buy_signals=mock_log_buy,
        log_closed_positions=mock_log_close,
        sl_filters=[],
        tp_filters=[]
    )

    # 2. Setup Mock State & Client
    mock_client = MagicMock()
    # Mock return values for spread placement
    mock_client.place_put_credit_spread.return_value = {
        'ok': True, 'atm_symbol': 'ATM_PE', 'hedge_symbol': 'HDG_PE', 'lot_size': 50
    }
    mock_client.get_option_ltp_by_symbol.side_effect = [100.0, 20.0] # ATM, HDG premiums
    
    mock_state = MagicMock(spec=OrbiterState)
    mock_state.client = mock_client
    mock_state.config = {
        'TOP_N': 1,
        'TRADE_SCORE': 60,
        'OPTION_PRODUCT_TYPE': 'I',
        'OPTION_PRICE_TYPE': 'MKT'
    }
    mock_state.active_positions = {}
    mock_state.filter_results_cache = {}
    mock_state.verbose_logs = True
    
    mock_state.client.SYMBOLDICT = {
        '26000': {'lp': '25000.0', 'company_name': 'NIFTY'}
    }

    # 3. Simulate high score for NIFTY
    scores = {'26000': 100.0}
    mock_syncer = MagicMock()

    # 4. Execute
    executor.rank_signals(mock_state, scores, mock_syncer)

    # 5. Verify Logging
    # Ensure log_buy_signals was called with the correct metadata
    mock_log_buy.assert_called_once()
    logged_signals = mock_log_buy.call_args[0][0]
    assert len(logged_signals) == 1
    # safe_ltp returns 'NSE|26000' as the default symbol if not found in SYMBOLDICT mapping
    assert logged_signals[0]['symbol'] == 'NSE|26000'
    assert logged_signals[0]['company_name'] == 'NIFTY'
    
    # Ensure it was added to active positions
    assert '26000' in mock_state.active_positions
    assert mock_state.active_positions['26000']['entry_net_premium'] == 80.0 # 100 - 20
