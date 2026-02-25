import numpy as np
import talib
import logging

logger = logging.getLogger("ORBITER")

class TechnicalAnalyzer:
    """
    Centralized Technical Analysis Engine.
    Calculates common indicators once per tick using efficient NumPy arrays.
    """
    
    def analyze(self, standardized_data: dict) -> dict:
        """
        Computes standard technical indicators from standardized OHLCV data.
        Returns a dictionary of indicators (e.g., {'ema5': 100.5, 'rsi': 55.2}).
        """
        indicators = {}
        
        # Extract Arrays
        close = standardized_data.get('close')
        high = standardized_data.get('high')
        low = standardized_data.get('low')
        
        if close is None or len(close) < 20:
            return indicators

        try:
            # 1. EMAs (Trend)
            indicators['ema5'] = self._ema(close, 5)
            indicators['ema9'] = self._ema(close, 9)
            indicators['ema20'] = self._ema(close, 20)
            indicators['ema50'] = self._ema(close, 50)
            
            # 2. Oscillators (Momentum)
            indicators['rsi'] = self._rsi(close, 14)
            indicators['adx'] = self._adx(high, low, close, 14)
            
            # 3. Volatility
            indicators['atr'] = self._atr(high, low, close, 14)
            
            # 4. SuperTrend (10, 3)
            st, st_dir = self._supertrend(high, low, close, 10, 3)
            indicators['supertrend'] = st
            indicators['supertrend_dir'] = st_dir

            # 5. Bollinger Bands (20, 2)
            u, m, l = self._bbands(close, 20, 2)
            indicators['bb_upper'] = u
            indicators['bb_middle'] = m
            indicators['bb_lower'] = l
            
        except Exception as e:
            logger.error(f"TechnicalAnalyzer Error: {e}")
            
        return indicators

    def _ema(self, close, period):
        try:
            val = talib.EMA(close, timeperiod=period)[-1]
            return round(float(val), 2) if not np.isnan(val) else 0.0
        except: return 0.0

    def _rsi(self, close, period):
        try:
            val = talib.RSI(close, timeperiod=period)[-1]
            return round(float(val), 2) if not np.isnan(val) else 50.0
        except: return 50.0

    def _adx(self, high, low, close, period):
        try:
            val = talib.ADX(high, low, close, timeperiod=period)[-1]
            return round(float(val), 2) if not np.isnan(val) else 0.0
        except: return 0.0

    def _atr(self, high, low, close, period):
        try:
            val = talib.ATR(high, low, close, timeperiod=period)[-1]
            return round(float(val), 2) if not np.isnan(val) else 0.0
        except: return 0.0

    def _bbands(self, close, period, dev):
        try:
            u, m, l = talib.BBANDS(close, timeperiod=period, nbdevup=dev, nbdevdn=dev, matype=0)
            return (
                round(float(u[-1]), 2), 
                round(float(m[-1]), 2), 
                round(float(l[-1]), 2)
            )
        except: return 0.0, 0.0, 0.0

    def _supertrend(self, high, low, close, period, multiplier):
        """
        Calculates SuperTrend. Returns (Value, Direction).
        Direction: 1 (Bullish/Green), -1 (Bearish/Red)
        """
        try:
            # Calculate ATR
            atr = talib.ATR(high, low, close, timeperiod=period)
            
            # Basic Upper and Lower Bands
            hl2 = (high + low) / 2
            basic_upper = hl2 + (multiplier * atr)
            basic_lower = hl2 - (multiplier * atr)
            
            final_upper = np.zeros(len(close))
            final_lower = np.zeros(len(close))
            st = np.zeros(len(close))
            trend = np.zeros(len(close)) # 1 for Bull, -1 for Bear
            
            for i in range(1, len(close)):
                # Final Upper Band
                if basic_upper[i] < final_upper[i-1] or close[i-1] > final_upper[i-1]:
                    final_upper[i] = basic_upper[i]
                else:
                    final_upper[i] = final_upper[i-1]
                
                # Final Lower Band
                if basic_lower[i] > final_lower[i-1] or close[i-1] < final_lower[i-1]:
                    final_lower[i] = basic_lower[i]
                else:
                    final_lower[i] = final_lower[i-1]
                
                # Trend Logic
                prev_trend = trend[i-1] if i > 0 else 1
                
                if prev_trend == 1: # Was Bullish
                    if close[i] <= final_lower[i-1]: # Breakdown
                        trend[i] = -1
                        st[i] = final_upper[i]
                    else: # Hold
                        trend[i] = 1
                        st[i] = final_lower[i]
                else: # Was Bearish
                    if close[i] >= final_upper[i-1]: # Breakout
                        trend[i] = 1
                        st[i] = final_lower[i]
                    else: # Hold
                        trend[i] = -1
                        st[i] = final_upper[i]

            return round(float(st[-1]), 2), int(trend[-1])

        except Exception as e:
            logger.error(f"SuperTrend Error: {e}")
            return 0.0, 0
