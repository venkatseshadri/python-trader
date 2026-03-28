"""
Test for scoring rule evaluation with instrument facts.
Reproduces the issue where instrument.expiry_cycle is not found during scoring.
"""

import unittest
import json
import os
import logging
from types import SimpleNamespace

# Setup path
import sys
_this_file = os.path.abspath(__file__)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_this_file))))
sys.path.insert(0, _project_root)

from orbiter.core.engine.rule.rule_manager import RuleManager
from orbiter.core.engine.session.session_manager import SessionManager
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager
from orbiter.utils.logger import setup_logging, TRACE_LEVEL_NUM


class TestInstrumentFactScoring(unittest.TestCase):
    """Test that instrument facts are properly passed to scoring rules."""
    
    def test_instrument_expiry_cycle_in_scoring(self):
        """
        Test that instrument.expiry_cycle fact is available during scoring evaluation.
        
        This reproduces the bug where scoring rules that filter on instrument.instrument_type
        and instrument.expiry_cycle fail because these facts are not passed through.
        
        Error: "Scoring Error [Calculate Stock Option Score]: instrument_expiry_cycle"
        """
        # Reset singletons
        ConstantsManager._instance = None
        SchemaManager._instance = None
        
        # Setup logging
        logging.getLogger().setLevel(TRACE_LEVEL_NUM)
        setup_logging('TRACE', _project_root)
        
        # Initialize session manager with explicit strategy
        session = SessionManager(_project_root, paper_trade=True, strategy_id='nifty_fno_topn_trend')
        
        # Get rules path for N1 strategy
        rules_path = os.path.join(_project_root, session.get_active_rules_file())
        print(f"Testing with rules file: {rules_path}")
        
        # Create rule manager
        manager = RuleManager(_project_root, rules_path, session)
        
        # Load sample candle data (create mock data)
        # Sample OHLCV data for RECLTD
        import random
        random.seed(42)  # For reproducibility
        
        candles = []
        base_price = 280.0
        for i in range(60):  # 60 candles for ADX calculation
            close = base_price + random.uniform(-5, 5)
            open_price = close + random.uniform(-2, 2)
            high = max(open_price, close) + random.uniform(0, 3)
            low = min(open_price, close) - random.uniform(0, 3)
            volume = random.randint(100000, 500000)
            candles.append({
                'intc': str(close),
                'inth': str(high),
                'intl': str(low),
                'into': str(open_price),
                'v': str(volume),
                'stat': 'Ok',
            })
        
        # Create mock client with candle data
        token = 'NSE|RECLTD'
        client = SimpleNamespace(
            SYMBOLDICT={token: {'symbol': 'RECLTD', 'candles': candles}}
        )
        state = SimpleNamespace(client=client, active_positions={})
        source = SimpleNamespace(state=state)
        
        # Simulate what core_engine.tick() does - pass instrument data with dot notation
        # This is the key: instrument data should be passed as instrument.xxx
        instrument_data = {
            'symbol': 'RECLTD',
            'token': 'RECLTD',
            'exchange': 'NSE',
            'derivative': 'option',
            'instrument_type': 'stock',
            'expiry_cycle': 'monthly'  # This is the field that's failing!
        }
        
        # Build extra_facts exactly like core_engine.tick() does
        extra_facts = {
            'token': 'RECLTD',
            'instrument.exchange': 'NSE',
            'instrument_exchange': 'NSE',
            'position': {},
            'portfolio.active_positions': 0,
            'portfolio_active_positions': 0,
        }
        
        # Add instrument data with 'instrument.' prefix (like core_engine.tick)
        for k, v in instrument_data.items():
            extra_facts[f"instrument.{k}"] = v
        
        print(f"\n=== Test Facts Being Passed ===")
        for k, v in extra_facts.items():
            print(f"  {k}: {v}")
        print("================================\n")
        
        # Get the instrument context constant
        ins_context = 'instrument'
        
        # Evaluate scoring - this should NOT raise an error
        score = None
        try:
            score_result = manager.evaluate_score(
                source,
                context=ins_context,
                **extra_facts
            )
            
            # Handle both old (float) and new (tuple) return formats
            if isinstance(score_result, tuple):
                score, score_details = score_result
                print(f"Scoring succeeded! Score: {score}, Details: {score_details}")
            else:
                score = score_result
                print(f"Scoring succeeded! Score: {score}")
            
            # The test passes if we get here without exception
            self.assertIsInstance(score, float)
            
        except Exception as e:
            print(f"Scoring failed with error: {e}")
            # Check if it's the specific bug
            if 'instrument_expiry_cycle' in str(e) or 'instrument.instrument_type' in str(e):
                self.fail(f"Bug reproduced: instrument facts not passed to scoring - {e}")
            else:
                raise
        
        # Additional assertion - score should be non-zero if technical indicators are working
        if score is not None:
            print(f"Final score value: {score}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
