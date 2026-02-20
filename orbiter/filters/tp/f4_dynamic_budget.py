import json
import os
from utils.utils import safe_float

class DynamicBudgetTP:
    def __init__(self):
        self.key = "TP_DYNAMIC_BUDGET"
        self.budget_master = {}
        self._load_master()

    def _load_master(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base_dir, 'data', 'budget_master.json')
        if os.path.exists(path):
            with open(path, 'r') as f:
                self.budget_master = json.load(f)
        else:
            print(f"⚠️ Budget Master not found at {path}. Using defaults.")

    def evaluate(self, position, ltp, data):
        """
        Evaluate if Dynamic Profit Target is hit.
        Target = (Historical_Budget - ORB_Size) * 0.75
        """
        # 1. Get Token & Symbol
        token = position.get('token')
        symbol = position.get('symbol')
        # Clean symbol for lookup (e.g. 'NSE|SBIN' -> 'SBIN')
        lookup_sym = token.split('|')[-1] if '|' in token else symbol
        
        # 2. Get Budget (Avg Intraday Range %)
        # Default to 2.0% if not found (conservative Nifty avg)
        budget_pct = self.budget_master.get(lookup_sym, 2.0)

        # 3. Get ORB Stats (Must be persisted in position)
        orb_high = safe_float(position.get('orb_high', 0))
        orb_low = safe_float(position.get('orb_low', 0))
        
        if orb_high == 0 or orb_low == 0:
            return {'hit': False}

        # Calculate Current ORB Size %
        # Using ORB Low as base for % calc
        orb_size_pts = orb_high - orb_low
        orb_size_pct = (orb_size_pts / orb_low) * 100.0

        # 4. Calculate Remaining Budget (Target Move %)
        # Law: Target = (Budget - Current_ORB) * 0.75
        remaining_budget_pct = (budget_pct - orb_size_pct) * 0.75
        
        # Safety Floor: Ensure we aim for at least 0.5% move if budget is exhausted
        if remaining_budget_pct < 0.5:
            remaining_budget_pct = 0.5

        # 5. Determine Target Price Level
        strategy = position.get('strategy', '')
        entry_price = safe_float(position.get('entry_price', 0))
        
        if entry_price == 0:
            return {'hit': False}

        if 'PUT' in strategy or 'LONG' in strategy: # Bullish
            # Target = Entry + (Entry * Remaining%)
            # Wait, better to base it off ORB High breakout level?
            # Research implies "run after the break".
            # Let's stick to Entry Price for PnL clarity.
            target_price = entry_price * (1 + remaining_budget_pct / 100.0)
            
            pct_gain = (ltp - entry_price) / entry_price * 100.0
            
            if ltp >= target_price:
                return {
                    'hit': True, 
                    'reason': f"🎯 Dynamic Target Hit: +{pct_gain:.2f}% (Budget: {budget_pct}%)",
                    'pct': pct_gain
                }

        elif 'CALL' in strategy or 'SHORT' in strategy: # Bearish
            target_price = entry_price * (1 - remaining_budget_pct / 100.0)
            
            # For short, pct gain is positive when price drops
            pct_gain = (entry_price - ltp) / entry_price * 100.0
            
            if ltp <= target_price:
                return {
                    'hit': True, 
                    'reason': f"🎯 Dynamic Target Hit: +{pct_gain:.2f}% (Budget: {budget_pct}%)",
                    'pct': pct_gain
                }

        return {'hit': False}
