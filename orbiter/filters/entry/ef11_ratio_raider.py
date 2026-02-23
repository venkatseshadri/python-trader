import numpy as np
import talib
from utils.utils import safe_float

def ratio_raider_filter(data, candles, **kwargs):
    """
    Refined Pairs Trading Filter for MCX Futures (GC/SI).
    """
    try:
        state = kwargs.get('state')
        current_token = kwargs.get('token')
        
        if not state or not current_token:
            return 0

        # Define Futures pairs
        symbol_map = {
            'GOLD': 'SILVER',
            'SILVER': 'GOLD',
            'GOLDM': 'SILVERM',
            'SILVERM': 'GOLDM',
            'COPPER': 'ALUMINIUM',
            'ALUMINIUM': 'COPPER'
        }
        
        current_symbol = ""
        for s in symbol_map.keys():
            if s in data.get('t', ''):
                current_symbol = s
                break
        
        if not current_symbol:
            return 0
            
        partner_symbol = symbol_map[current_symbol]
        
        # Find partner's live LTP
        partner_data = None
        for token, val in state.client.SYMBOLDICT.items():
            if partner_symbol in val.get('t', ''):
                partner_data = val
                break
        
        if not partner_data or safe_float(partner_data.get('lp')) == 0:
            return 0
            
        ltp_a = safe_float(data.get('lp')) # Current
        ltp_b = safe_float(partner_data.get('lp')) # Partner
        
        # Calculate Ratio (Base A / Base B)
        # To maintain a stable ratio direction, always use Gold/Silver alphabetical
        if current_symbol < partner_symbol:
            current_ratio = ltp_a / ltp_b
            is_primary = True
        else:
            current_ratio = ltp_b / ltp_a
            is_primary = False
            
        # Maintain ratio history in state for Z-Score
        hist_key = f"ratio_{min(current_symbol, partner_symbol)}_{max(current_symbol, partner_symbol)}"
        if not hasattr(state, 'pair_histories'):
            state.pair_histories = {}
        
        if hist_key not in state.pair_histories:
            state.pair_histories[hist_key] = []
            
        state.pair_histories[hist_key].append(current_ratio)
        if len(state.pair_histories[hist_key]) > 60: # 60 minute window for sharper signals
            state.pair_histories[hist_key].pop(0)
            
        if len(state.pair_histories[hist_key]) < 20:
            return 0
            
        mean_ratio = np.mean(state.pair_histories[hist_key])
        std_ratio = np.std(state.pair_histories[hist_key])
        if std_ratio == 0: return 0
        
        zscore = (current_ratio - mean_ratio) / std_ratio
        
        # Signal Logic (Z-Score Threshold = 2.0)
        # If Ratio (A/B) is low -> A is cheap, B is expensive -> Buy A
        if is_primary:
            if zscore < -2.0: return 0.55 # Buy Primary (Gold)
            if zscore > 2.0: return -0.55 # Sell Primary
        else:
            # We are the partner (B). If Ratio (A/B) is high -> B is cheap -> Buy B
            if zscore > 2.0: return 0.55 # Buy Partner (Silver)
            if zscore < -2.0: return -0.55 # Sell Partner
            
        return 0
        
    except Exception:
        return 0
