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
        logger.trace(f"[TechnicalAnalyzer.analyze] START - close={type(close)}, high={type(high)}, low={type(low)}")
        
        if close is None or len(close) < 14:
            logger.trace(f"[TechnicalAnalyzer.analyze] EARLY RETURN - close is None or len < 14: close={close is not None}, len={len(close) if close is not None else 'N/A'}")
            return indicators

        logger.trace(f"[TechnicalAnalyzer.analyze] close[:3]={close[:3] if len(close) > 0 else 'empty'}, len={len(close)}")
        logger.trace(f"[TechnicalAnalyzer.analyze] high[:3]={high[:3] if len(high) > 0 else 'empty'}, len={len(high)}")
        logger.trace(f"[TechnicalAnalyzer.analyze] low[:3]={low[:3] if len(low) > 0 else 'empty'}, len={len(low)}")
        
        try:
            # 1. EMAs (Trend)
            indicators['index.ema5'] = indicators['index_ema5'] = self._ema(close, 5)
            indicators['index.ema9'] = indicators['index_ema9'] = self._ema(close, 9)
            indicators['index.ema20'] = indicators['index_ema20'] = self._ema(close, 20)
            indicators['index.ema50'] = indicators['index_ema50'] = self._ema(close, 50)
            indicators['index.ema_fast'] = indicators['index_ema_fast'] = indicators['index.ema5']
            indicators['index.ema_slow'] = indicators['index_ema_slow'] = indicators['index.ema20']
            
            # 2. Oscillators (Momentum)
            indicators['index.rsi'] = indicators['index_rsi'] = self._rsi(close, 14)
            indicators['index.adx'] = indicators['index_adx'] = self._adx(high, low, close, 14)
            
            # 3. Volatility
            indicators['index.atr'] = indicators['index_atr'] = self._atr(high, low, close, 14)
            
            # 4. SuperTrend (10, 3)
            st, st_dir = self._supertrend(high, low, close, 10, 3)
            indicators['index.supertrend'] = indicators['index_supertrend'] = st
            indicators['index.supertrend_dir'] = indicators['index_supertrend_dir'] = st_dir

            # 5. Bollinger Bands (20, 2)
            u, m, l = self._bbands(close, 20, 2)
            indicators['index.bb_upper'] = indicators['index_bb_upper'] = u
            indicators['index.bb_middle'] = indicators['index_bb_middle'] = m
            indicators['index.bb_lower'] = indicators['index_bb_lower'] = l
            
        except Exception as e:
            logger.error(f"TechnicalAnalyzer Error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
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
            logger.trace(f"[_adx] START - high type={type(high)}, low type={type(low)}, close type={type(close)}")
            logger.trace(f"[_adx] high[:5]={high[:5] if hasattr(high, '__getitem__') and len(high) > 0 else 'N/A'}")
            logger.trace(f"[_adx] low[:5]={low[:5] if hasattr(low, '__getitem__') and len(low) > 0 else 'N/A'}")
            logger.trace(f"[_adx] close[:5]={close[:5] if hasattr(close, '__getitem__') and len(close) > 0 else 'N/A'}")
            logger.trace(f"[_adx] len(close)={len(close) if hasattr(close, '__len__') else 'no len'}")
            
            # Check for NaN in input data
            if hasattr(high, '__iter__') and len(high) > 0:
                high_arr = np.array(high)
                logger.trace(f"[_adx] high has NaN={np.any(np.isnan(high_arr))}, min={np.min(high_arr)}, max={np.max(high_arr)}")
            if hasattr(low, '__iter__') and len(low) > 0:
                low_arr = np.array(low)
                logger.trace(f"[_adx] low has NaN={np.any(np.isnan(low_arr))}, min={np.min(low_arr)}, max={np.max(low_arr)}")
            if hasattr(close, '__iter__') and len(close) > 0:
                close_arr = np.array(close)
                logger.trace(f"[_adx] close has NaN={np.any(np.isnan(close_arr))}, min={np.min(close_arr)}, max={np.max(close_arr)}")
            
            # Check if high <= low (flat data causes NaN)
            if hasattr(high, '__iter__') and hasattr(low, '__iter__') and len(high) > 0 and len(low) > 0:
                flat_count = np.sum(np.array(high) <= np.array(low))
                logger.trace(f"[_adx] candles where high <= low: {flat_count}/{len(high)}")
            
            adx_arr = talib.ADX(high, low, close, timeperiod=period)
            val = adx_arr[-1]
            logger.trace(f"[_adx] talib.ADX result array[:5]={adx_arr[:5]}, last={val}")
            
            result = round(float(val), 2) if not np.isnan(val) else 0.0
            logger.trace(f"[_adx] FINAL result={result}")
            return result
        except Exception as e:
            logger.trace(f"[_adx] EXCEPTION: {e}")
            import traceback
            logger.trace(f"[_adx] traceback: {traceback.format_exc()}")
            return 0.0

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
