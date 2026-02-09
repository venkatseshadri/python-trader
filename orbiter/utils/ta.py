def calculate_ema(prices, period):
    """
    Calculate Exponential Moving Average (EMA)
    prices: list of floats [1456.60, 1457.20, 1458.10...]
    period: int (5, 9, 20...)
    Returns: float (latest EMA value)
    """
    if not prices or len(prices) < period:
        return 0.0
    
    prices = [float(p) for p in prices[-period*2:]]  # Last 2x period for accuracy
    
    if len(prices) == 0:
        return 0.0
    
    # Smoothing factor k = 2/(N+1)
    k = 2 / (period + 1)
    
    # Initialize EMA with SMA of first period
    ema = sum(prices[:period]) / period
    
    # Calculate EMA iteratively
    for price in prices[period:]:
        ema = price * k + ema * (1 - k)
    
    return round(ema, 2)

def calculate_rsi(prices, period=14):
    """RSI for SL filter F4"""
    if len(prices) < period + 1:
        return 50.0
    
    deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

def calculate_atr(highs, lows, closes, period=14):
    """ATR for SL filter F6"""
    trs = []
    for i in range(1, len(highs)):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - closes[i-1])
        tr3 = abs(lows[i] - closes[i-1])
        trs.append(max(tr1, tr2, tr3))
    
    if len(trs) < period:
        return 0.0
    
    atr = sum(trs[-period:]) / period
    return round(atr, 2)
