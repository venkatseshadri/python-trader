# orbiter/core/market_data.py

import logging
import threading

logger = logging.getLogger("ORBITER")


class MarketData:
    """Handles all data operations - priming, live feed, source selection."""

    @staticmethod
    def prime_and_subscribe(client, symbols: list) -> bool:
        """
        Prime historical data and start live feed.
        App doesn't need to know lookback/interval details.
        """
        if not client:
            return False
        
        try:
            logger.info("⚡ PRIMING DATA...")
            
            # Get strategy parameters for lookback/interval
            # These come from strategy config, not hardcoded here
            lookback = 300  # 300 mins = ~60 candles for ADX warmup (was 120)
            interval = 5   # Default
            
            client.start_live_feed(symbols)
            
            def _bg_prime():
                try:
                    client._priming_interval = interval
                    client.prime_candles(symbols, lookback_mins=lookback)
                    logger.info("✅ Background Data Priming Complete.")
                except Exception as e:
                    logger.error(f"❌ Priming failed: {e}")

            threading.Thread(target=_bg_prime, daemon=True).start()
            return True
            
        except Exception as e:
            logger.error(f"❌ Data init failed: {e}")
            return False
