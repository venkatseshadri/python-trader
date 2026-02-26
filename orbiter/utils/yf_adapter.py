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
