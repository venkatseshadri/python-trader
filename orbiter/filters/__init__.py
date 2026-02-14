# orbiter/filters/__init__.py
"""
🎯 Unified Filter Factory
Now truly segment-agnostic. Segment-specific behavior is driven by parameters
passed from config (e.g., ORB window times).
"""

# Common Agnostic Filters
from .common.orb import orb_filter
from .common.ema5 import price_above_5ema_filter
from .common.ema_cross import ema5_above_9ema_filter
from .common.supertrend import supertrend_filter

# Exit Filters
from .sl.f1_price_increase_10 import check_sl as sl_price_increase_10
from .tp.f1_premium_decay_10 import check_tp as tp_premium_decay_10
from .tp.f2_trailing_sl import check_trailing_sl as tp_trailing_sl
from .tp.f3_retracement_sl import check_retracement_sl as tp_retracement_sl

class Filter:
    def __init__(self, key, filter_type, evaluate):
        self.key = key
        self.filter_type = filter_type
        self.evaluate = evaluate

def get_filters(filter_type, segment_name=None):
    """Returns the set of active filters. Agnostic to segment_name as logic is parameterized."""
    
    FILTERS = [
        # Entry Filters
        Filter('ef1_orb', 'entry', orb_filter),
        Filter('ef2_price_above_5ema', 'entry', price_above_5ema_filter),
        Filter('ef3_5ema_above_9ema', 'entry', ema5_above_9ema_filter),
        Filter('ef4_supertrend', 'entry', supertrend_filter),
        
        # Exit Filters
        Filter('sf1_price_increase_10', 'sl', lambda position, ltp, data: sl_price_increase_10(position, ltp, data)),
        Filter('tf1_premium_decay_10', 'tp', lambda position, ltp, data: tp_premium_decay_10(position, ltp, data)),
        Filter('tf2_trailing_sl', 'tp', lambda position, ltp, data: tp_trailing_sl(position, ltp, data)),
        Filter('tf3_retracement_sl', 'tp', lambda position, ltp, data: tp_retracement_sl(position, ltp, data)),
    ]
    
    return [flt for flt in FILTERS if flt.filter_type == filter_type]
