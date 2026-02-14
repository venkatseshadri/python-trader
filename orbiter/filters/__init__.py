# Filters
from .entry.f1_orb import orb_filter
from .entry.f2_price_above_5ema import price_above_5ema_filter
from .entry.f3_5ema_above_9ema import ema5_above_9ema_filter
from .entry.f4_supertrend import supertrend_filter
from .entry.f5_ema_scope import ema_scope_filter
from .entry.f6_ema_gap import ema_gap_expansion_filter
from .sl.f1_price_increase_10 import check_sl as sl_price_increase_10
from .tp.f1_premium_decay_10 import check_tp as tp_premium_decay_10
from .tp.f2_trailing_sl import check_trailing_sl as tp_trailing_sl
from .tp.f3_retracement_sl import check_retracement_sl as tp_retracement_sl
from .sl.f1_below_5ema import sl_below_5ema
from .sl.f2_5ema_below_9ema import sl_5ema_below_9ema
from .sl.f3_below_orb_low import sl_below_orb_low
from .sl.f4_rsi_oversold import sl_rsi_oversold
from .sl.f5_volume_dryup import sl_volume_dryup
from .sl.f6_atr_spike import sl_atr_spike
from .sl.f7_red_candle import sl_red_candle_weakness
from .sl.f8_below_vwap import sl_below_vwap
from .sl.f9_macd_bearish import sl_macd_bearish
from .sl.f10_support_broken import sl_support_broken


class Filter:
    def __init__(self, key, filter_type, evaluate):
        self.key = key
        self.filter_type = filter_type
        self.evaluate = evaluate


def _hit_result(hit, reason=None, pct=None):
    result = {'hit': bool(hit)}
    if pct is not None:
        result['pct'] = pct
    if reason:
        result['reason'] = reason
    return result

FILTERS = [
    Filter('ef1_orb', 'entry', orb_filter),
    Filter('ef2_price_above_5ema', 'entry', price_above_5ema_filter),
    Filter('ef3_5ema_above_9ema', 'entry', ema5_above_9ema_filter),
    Filter('ef4_supertrend', 'entry', supertrend_filter),
    Filter('ef5_ema_scope', 'entry', ema_scope_filter),
    Filter('ef6_ema_gap', 'entry', ema_gap_expansion_filter),
    # Only keep the 10% premium SL/TP; all other SL filters are disabled.
    Filter('sf1_price_increase_10', 'sl', lambda position, ltp, data: sl_price_increase_10(position, ltp, data)),
    Filter('tf1_premium_decay_10', 'tp', lambda position, ltp, data: tp_premium_decay_10(position, ltp, data)),
    Filter('tf2_trailing_sl', 'tp', lambda position, ltp, data: tp_trailing_sl(position, ltp, data)),
    Filter('tf3_retracement_sl', 'tp', lambda position, ltp, data: tp_retracement_sl(position, ltp, data)),
]


def get_filters(filter_type):
    return [flt for flt in FILTERS if flt.filter_type == filter_type]

