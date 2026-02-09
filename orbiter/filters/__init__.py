# Filters
from .entry.f1_orb import orb_filter
from .entry.f2_price_above_5ema import price_above_5ema_filter
from .entry.f3_5ema_above_9ema import ema5_above_9ema_filter
from .sl.f1_price_increase_10 import check_sl as sl_price_increase_10
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
    Filter('sf1_price_increase_10', 'sl', lambda position, ltp, data: sl_price_increase_10(position, ltp)),
    Filter('sf2_below_5ema', 'sl', lambda position, ltp, data: _hit_result(sl_below_5ema(data), 'below_5ema')),
    Filter('sf3_5ema_below_9ema', 'sl', lambda position, ltp, data: _hit_result(sl_5ema_below_9ema(data), '5ema_below_9ema')),
    Filter('sf4_below_orb_low', 'sl', lambda position, ltp, data: _hit_result(sl_below_orb_low(data), 'below_orb_low')),
    Filter('sf5_rsi_oversold', 'sl', lambda position, ltp, data: _hit_result(sl_rsi_oversold(data), 'rsi_oversold')),
    Filter('sf6_volume_dryup', 'sl', lambda position, ltp, data: _hit_result(sl_volume_dryup(data), 'volume_dryup')),
    Filter('sf7_atr_spike', 'sl', lambda position, ltp, data: _hit_result(sl_atr_spike(data), 'atr_spike')),
    Filter('sf8_red_candle', 'sl', lambda position, ltp, data: _hit_result(sl_red_candle_weakness(data), 'red_candle')),
    Filter('sf9_below_vwap', 'sl', lambda position, ltp, data: _hit_result(sl_below_vwap(data), 'below_vwap')),
    Filter('sf10_macd_bearish', 'sl', lambda position, ltp, data: _hit_result(sl_macd_bearish(data), 'macd_bearish')),
    Filter('sf11_support_broken', 'sl', lambda position, ltp, data: _hit_result(sl_support_broken(data), 'support_broken')),
]


def get_filters(filter_type):
    return [flt for flt in FILTERS if flt.filter_type == filter_type]

