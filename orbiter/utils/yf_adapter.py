# orbiter/utils/yf_adapter.py
"""
Yahoo Finance adapter for getting market regime indicators.
Used for dynamic strategy selection (not for trade scoring).
"""
import yfinance as yf
import talib
import logging

logger = logging.getLogger("ORBITER")

# Mapping of indices to yfinance symbols
INDEX_SYMBOLS = {
    'SENSEX': '^BSESN',
    'NIFTY': '^NSEI',
    'NIFTY_BANK': '^NSEBANK',
    'BANKEX': '^BSEBK',
}

def get_market_adx(index_name: str = 'SENSEX', interval: str = '5m') -> float:
    """
    Get current ADX for an index from Yahoo Finance.
    
    Args:
        index_name: Index name (SENSEX, NIFTY, BANKEX)
        interval: Candle interval ('1m', '5m', '15m')
    
    Returns:
        ADX value, or -1.0 if calculation fails
    """
    symbol = INDEX_SYMBOLS.get(index_name.upper(), '^BSESN')
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period='1d', interval=interval)
        
        if df.empty:
            logger.warning(f"YF: No data for {symbol}")
            return -1.0
            
        candle_count = len(df)
        logger.info(f"YF: Got {candle_count} candles for {symbol} at {interval}")
        
        # Need at least 14 candles for ADX 14
        if candle_count < 14:
            # Try smaller interval
            if interval == '5m':
                return get_market_adx(index_name, '1m')
            logger.warning(f"YF: Not enough candles ({candle_count}) for ADX")
            return -1.0
        
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        
        adx = talib.ADX(high, low, close, timeperiod=14)
        adx_value = round(float(adx[-1]), 2)
        
        logger.info(f"YF: {index_name} ADX ({interval}) = {adx_value}")
        return adx_value
        
    except Exception as e:
        logger.error(f"YF: Error getting ADX for {symbol}: {e}")
        return -1.0


def get_market_regime(index_name: str = 'SENSEX') -> str:
    """
    Determine market regime based on ADX.
    
    Returns:
        'trending' if ADX >= 25
        'sideways' if ADX < 25
    """
    adx = get_market_adx(index_name)
    if adx < 0:
        return 'unknown'
    return 'trending' if adx >= 25 else 'sideways'


def get_all_indicators(index_name: str = 'SENSEX', interval: str = '5m') -> dict:
    """
    Get all technical indicators from Yahoo Finance for fallback.
    
    Returns:
        dict with keys: adx, ema_fast, ema_slow, supertrend_dir, supertrend
    """
    symbol = INDEX_SYMBOLS.get(index_name.upper(), '^BSESN')
    
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period='1d', interval=interval)
        
        if df.empty or len(df) < 14:
            # Try smaller interval if 5m doesn't have enough data
            if interval == '5m':
                logger.info(f"YF: Not enough 5m candles ({len(df)}), trying 1m interval")
                ticker_1m = yf.Ticker(symbol)
                df = ticker_1m.history(period='1d', interval='1m')
                if df.empty or len(df) < 14:
                    logger.warning(f"YF: No data for {symbol} (tried 1m, got {len(df)} rows)")
                    return {}
                interval = '1m'
            else:
                logger.warning(f"YF: No data for {symbol}")
                return {}
        
        high = df['High'].values
        low = df['Low'].values
        close = df['Close'].values
        
        # Calculate all indicators
        adx = talib.ADX(high, low, close, timeperiod=14)
        ema_fast = talib.EMA(close, timeperiod=5)
        ema_slow = talib.EMA(close, timeperiod=20)
        
        # SuperTrend calculation
        atr = talib.ATR(high, low, close, timeperiod=10)
        hl2 = (high + low) / 2
        upper = hl2 + (3 * atr)
        lower = hl2 - (3 * atr)
        
        # Simple SuperTrend direction (1 = bull, -1 = bear)
        st_dir = 1 if close[-1] > lower[-1] else -1
        
        return {
            'adx': round(float(adx[-1]), 2),
            'ema_fast': round(float(ema_fast[-1]), 2),
            'ema_slow': round(float(ema_slow[-1]), 2),
            'supertrend_dir': st_dir,
            'supertrend': round(float(atr[-1] * 3), 2),  # ATR-based value
        }
        
    except Exception as e:
        logger.error(f"YF: Error getting indicators for {symbol}: {e}")
        return {}
