import pytest
import pandas as pd
import numpy as np
import os
import json
import talib
from filters.entry.f4_supertrend import supertrend_filter

def load_ta_snapshots():
    path = os.path.join(os.path.dirname(__file__), '../data/ta_golden_values.json')
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
        return data['snapshots']

SNAPSHOTS = load_ta_snapshots()

@pytest.mark.parametrize("snapshot", SNAPSHOTS)
def test_indicators_against_golden_values(snapshot, mocker):
    """
    Validates EMA and SuperTrend calculations against manually verified chart values.
    Uses talib with compatibility=1 (Metastock) to match bot's runtime behavior.
    """
    # 1. Load Data Chunk
    csv_path = os.path.join(os.path.dirname(__file__), '../data/nifty_ta_chunk.csv')
    df = pd.read_csv(csv_path, header=None, names=['date', 'open', 'high', 'low', 'close', 'vol'])
    
    # Filter history up to the specific snapshot timestamp
    df_filtered = df[df['date'] <= f"2025-07-21 {snapshot['timestamp']}"]
    closes = np.array(df_filtered['close'].tolist(), dtype=float)

    # 2. Verify EMA 5 and EMA 9 using TA-Lib with Metastock compatibility
    try:
        talib.set_compatibility(1)
        ema5_values = talib.EMA(closes, timeperiod=5)
        ema9_values = talib.EMA(closes, timeperiod=9)
    finally:
        talib.set_compatibility(0)

    ema5_calc = round(ema5_values[-1], 2)
    ema9_calc = round(ema9_values[-1], 2)

    print(f"\n--- Snapshot: {snapshot['timestamp']} ---")
    print(f"EMA5: Calc={ema5_calc}, Golden={snapshot['ema_5']} (diff={abs(ema5_calc-snapshot['ema_5']):.2f})")
    print(f"EMA9: Calc={ema9_calc}, Golden={snapshot['ema_9']} (diff={abs(ema9_calc-snapshot['ema_9']):.2f})")

    assert abs(ema5_calc - snapshot['ema_5']) <= 0.5
    assert abs(ema9_calc - snapshot['ema_9']) <= 1.0

    # 3. Verify SuperTrend
    # Convert filtered DF to Bot's expected Candle List format
    candle_data = []
    for _, row in df_filtered.iterrows():
        candle_data.append({
            'stat': 'Ok',
            'inth': str(row['high']),
            'intl': str(row['low']),
            'intc': str(row['close']),
            'time': row['date']
        })

    # Setup Mocks for Config (ensure standard params)
    mocker.patch('filters.entry.f4_supertrend.SUPER_TREND_PERIOD', 10)
    mocker.patch('filters.entry.f4_supertrend.SUPER_TREND_MULTIPLIER', 3)
    mocker.patch('filters.entry.f4_supertrend.SCORE_CAP_ST_PCT', 0.10)

    tick_data = {'lp': str(snapshot['close'])}
    st_result = supertrend_filter(tick_data, candle_data, token='26000')

    print(f"ST:   Calc={st_result['supertrend']:.2f}, Golden={snapshot['supertrend_10_3']} (diff={abs(st_result['supertrend']-snapshot['supertrend_10_3']):.2f})")
    
    assert abs(st_result['supertrend'] - snapshot['supertrend_10_3']) <= 1.0
