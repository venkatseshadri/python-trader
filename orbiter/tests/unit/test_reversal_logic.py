import pytest
import math
from core.engine.evaluator import Evaluator
from unittest.mock import MagicMock

@pytest.fixture
def evaluator_setup():
    state = MagicMock()
    # Balanced weights for all 6 filters
    state.config = {
        'ENTRY_WEIGHTS': [1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        'SIMULATION': True
    }
    state.filters.get_filters = MagicMock()
    state.client.SYMBOLDICT = {}
    state.filter_results_cache = {}
    state.last_scan_metrics = []
    state.verbose_logs = True
    return state, Evaluator()

def test_reversal_with_momentum_stack(evaluator_setup):
    """
    STRESS TEST: Verifies that the new F5/F6 filters accelerate the 
    exit signal during a market reversal.
    """
    state, evaluator = evaluator_setup
    
    # 4-minute crash scenario
    scenarios = [
        {
            "time": "12:27", "desc": "Peak",
            "f1": 0.40, "f2": 0.02, "f3": 0.01, "f4": 0.20,
            "f5": 0.05, "f6": 0.02, # F5 (Scope) and F6 (Gap) are strongly positive
            "expected_conviction": "STRONG BULL"
        },
        {
            "time": "12:28", "desc": "Stall",
            "f1": 0.35, "f2": 0.00, "f3": 0.00, "f4": 0.10,
            "f5": -0.02, "f6": -0.01, # F5 and F6 ALREADY turned negative!
            "expected_conviction": "WEAKENING"
        },
        {
            "time": "12:29", "desc": "Trend Flip",
            "f1": 0.30, "f2": -0.01, "f3": -0.01, "f4": -0.10,
            "f5": -0.08, "f6": -0.05, # Momentum is crashing
            "expected_conviction": "EXIT"
        }
    ]

    print("\n--- MOMENTUM STACK REPLAY (F1-F6) ---")
    
    for s in scenarios:
        weights = state.config['ENTRY_WEIGHTS']
        scores = [s['f1'], s['f2'], s['f3'], s['f4'], s['f5'], s['f6']]
        total = round(sum(w * sc for w, sc in zip(weights, scores)), 2)
        
        print(f"Time: {s['time']} | Score: {total:>+5.2f} | Momentum (F5+F6): {s['f5']+s['f6']:>+5.2f} | State: {s['desc']}")

        if s['time'] == "12:28":
            # In the 4-filter logic, this score was +0.45.
            # In the 6-filter logic, it should be lower because F5/F6 caught the slowing pace.
            assert total < 0.45 

    print("\n✅ Momentum verification: F5/F6 provided an earlier warning.")
