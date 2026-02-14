import pytest
import pandas as pd
import os
import json
from utils.ta import calculate_ema

def test_ema_against_golden_values():
    """
    Validates EMA calculation against manually verified chart values.
    Verification Date: 2025-07-21 10:54:00 (1-min timeframe)
    Verified by: User (Manual Chart)
    """
    # 1. Load Data Chunk
    csv_path = os.path.join(os.path.dirname(__file__), '../data/nifty_ta_chunk.csv')
    golden_path = os.path.join(os.path.dirname(__file__), '../data/ta_golden_values.json')
    
    df = pd.read_csv(csv_path, header=None, names=['date', 'open', 'high', 'low', 'close', 'vol'])
    # Filter up to the golden timestamp (12:00 PM)
    df = df[df['date'] <= '2025-07-21 12:00:00']
    
    with open(golden_path) as f:
        golden = json.load(f)['golden_values']

    # 2. Extract Close Prices
    closes = df['close'].tolist()
    
    # 3. Calculate EMAs
    ema5_calc = calculate_ema(closes, period=5)
    ema9_calc = calculate_ema(closes, period=9)

    # 4. Assert (Allowing for small rounding differences between charting platforms)
    assert abs(ema5_calc - golden['ema_5']) <= 0.5
    assert abs(ema9_calc - golden['ema_9']) <= 1.0

    print(f"✅ EMA5 Calc: {ema5_calc} vs Golden: {golden['ema_5']}")
    print(f"✅ EMA9 Calc: {ema9_calc} vs Golden: {golden['ema_9']}")

def test_supertrend_against_golden_values(mocker):
    """
    Validates SuperTrend calculation against manually verified chart values.
    Verification Date: 2025-07-21 10:54:00 (1-min timeframe)
    Value: 25060.40 (10, 3)
    """
    from filters.entry.f4_supertrend import supertrend_filter
    
    # 1. Load Data Chunk
    csv_path = os.path.join(os.path.dirname(__file__), '../data/nifty_ta_chunk.csv')
    golden_path = os.path.join(os.path.dirname(__file__), '../data/ta_golden_values.json')
    
    df = pd.read_csv(csv_path, header=None, names=['date', 'open', 'high', 'low', 'close', 'vol'])
    # Filter up to the golden timestamp (12:00 PM)
    df = df[df['date'] <= '2025-07-21 12:00:00']
    
    with open(golden_path) as f:
        golden = json.load(f)['golden_values']

    # 2. Convert CSV to Bot's expected Candle List format
    candle_data = []
    for _, row in df.iterrows():
        candle_data.append({
            'stat': 'Ok',
            'inth': str(row['high']),
            'intl': str(row['low']),
            'intc': str(row['close']),
            'time': row['date']
        })

    # 3. Setup Mocks for Config
    mocker.patch('filters.entry.f4_supertrend.SUPER_TREND_PERIOD', 10)
    mocker.patch('filters.entry.f4_supertrend.SUPER_TREND_MULTIPLIER', 3)
    mocker.patch('filters.entry.f4_supertrend.SCORE_CAP_ST_PCT', 0.10)
    mocker.patch('filters.entry.f4_supertrend.VERBOSE_LOGS', True)

    # 4. Execute Filter (Last row is the 10:54 candle)
    tick_data = {'lp': str(golden['close'])}
    result = supertrend_filter(tick_data, candle_data, token='26000')

    # 5. Assert
    # Golden ST: 25060.40
    assert abs(result['supertrend'] - golden['supertrend_10_3']) <= 1.0
    print(f"✅ SuperTrend Calc: {result['supertrend']} vs Golden: {golden['supertrend_10_3']}")
