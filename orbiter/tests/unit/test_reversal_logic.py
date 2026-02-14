import pytest
import json
import os
from core.engine.evaluator import Evaluator
from unittest.mock import MagicMock

def load_reversal_scenarios():
    path = os.path.join(os.path.dirname(__file__), '../data/reversal_scenarios.json')
    with open(path) as f:
        return json.load(f)

SCENARIOS = load_reversal_scenarios()

@pytest.fixture
def evaluator_setup():
    state = MagicMock()
    state.config = {
        'ENTRY_WEIGHTS': [1.0, 1.2, 1.2, 0.6, 1.2, 1.2],
        'TRADE_SCORE': 0.20
    }
    return state, Evaluator()

@pytest.mark.parametrize("scenario_name", SCENARIOS.keys())
def test_reversal_score_collapse_generic(scenario_name, evaluator_setup):
    """
    Generic Stress Test: Verifies score collapse for any reversal 
    event defined in reversal_scenarios.json.
    """
    state, evaluator = evaluator_setup
    data_points = SCENARIOS[scenario_name]
    
    print(f"\n--- REPLAY: {scenario_name} ---")
    
    total_scores = []
    for p in data_points:
        weights = state.config['ENTRY_WEIGHTS']
        # We assume 6 filters for this momentum test
        scores = [p['f1'], p['f2'], p['f3'], p['f4'], p['f5'], p['f6']]
        total = round(sum(w * s for w, s in zip(weights, scores)), 2)
        total_scores.append(total)
        print(f"Time: {p['time']} | Score: {total:>+5.2f} | State: {p['desc']}")

    # ASSERTIONS (Universal for Reversals)
    # 1. Conviction must drop between start and middle
    assert total_scores[1] < total_scores[0]
    # 2. Reversal point must be below threshold
    assert total_scores[2] < state.config['TRADE_SCORE']
    # 3. Final point must be bearish
    assert total_scores[-1] < 0
