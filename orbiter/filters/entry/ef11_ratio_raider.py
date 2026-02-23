import numpy as np
import talib
from utils.utils import safe_float

def ratio_raider_filter(data, candles, **kwargs):
    """
    Pairs Trading / Ratio Arbitrage Filter (GC vs SI)
    Only active during SIDEWAYS market.
    """
    try:
        state = kwargs.get('state')
        current_token = kwargs.get('token') # e.g. MCX|454818 (GOLD)
        
        if not state or not current_token:
            return 0

        # Define the primary pair (Gold and Silver)
        # Using symbols from mcx_futures_map to be precise
        # GOLD: MCX|454818, SILVER: MCX|451666
        # Note: We use the base symbols for logic
        
        symbol_map = {
            'GOLD': 'SILVER',
            'SILVER': 'GOLD',
            'GOLDM': 'SILVERM',
            'SILVERM': 'GOLDM'
        }
        
        current_symbol = ""
        for s in symbol_map.keys():
            if s in data.get('t', ''): # tradingsymbol
                current_symbol = s
                break
        
        if not current_symbol:
            return 0
            
        partner_symbol = symbol_map[current_symbol]
        
        # Find partner's live data
        partner_data = None
        for token, val in state.client.SYMBOLDICT.items():
            if partner_symbol in val.get('t', ''):
                partner_data = val
                break
        
        if not partner_data or safe_float(partner_data.get('lp')) == 0:
            return 0
            
        ltp_a = safe_float(data.get('lp'))
        ltp_b = safe_float(partner_data.get('lp'))
        
        # Calculate current ratio
        # Always A/B where A is Gold, B is Silver for consistency
        if 'GOLD' in current_symbol:
            current_ratio = ltp_a / ltp_b
        else:
            current_ratio = ltp_b / ltp_a
            
        # We need historical ratio for Z-Score
        # For simplicity in this filter, we check if Ratio is stretched 
        # compared to its opening ratio or a fixed benchmark.
        # Ideally, we'd use a rolling window, but filter has limited state.
        
        # 🧠 CRITICAL: Since filters are stateless, we'll store the ratio 
        # in the partner's data dict or a global state cache.
        if not hasattr(state, 'ratio_history'):
            state.ratio_history = []
            
        state.ratio_history.append(current_ratio)
        if len(state.ratio_history) > 120: # 2 hour window
            state.ratio_history.pop(0)
            
        if len(state.ratio_history) < 30:
            return 0
            
        mean_ratio = np.mean(state.ratio_history)
        std_ratio = np.std(state.ratio_history)
        if std_ratio == 0: return 0
        
        zscore = (current_ratio - mean_ratio) / std_ratio
        
        # Signal Logic
        # If I am GOLD and Z is low -> Buy Gold
        # If I am SILVER and Z is high -> Buy Silver
        if 'GOLD' in current_symbol:
            if zscore < -2.0: return 0.55 # Buy Gold
            if zscore > 2.0: return -0.55 # Sell Gold
        else: # I am SILVER
            if zscore > 2.0: return 0.55 # Buy Silver (it's undervalued relative to Gold)
            if zscore < -2.0: return -0.55 # Sell Silver
            
        return 0
        
    except Exception:
        return 0
