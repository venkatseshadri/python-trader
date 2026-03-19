# orbiter/core/tick_processor.py

import logging
import threading
import time
from collections import defaultdict
from typing import Callable, Dict, List, Any, Optional

logger = logging.getLogger("ORBITER")


class TickBuffer:
    """Stores ticks per symbol for batch processing."""
    
    def __init__(self):
        self._buffer: Dict[str, List[Dict]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def add(self, symbol: str, tick: Dict[str, Any]):
        """Add a tick to the buffer for a symbol."""
        with self._lock:
            self._buffer[symbol].append(tick)
    
    def get_all_and_clear(self) -> Dict[str, List[Dict]]:
        """Get all buffered ticks and clear the buffer."""
        with self._lock:
            ticks = dict(self._buffer)
            self._buffer.clear()
            return ticks
    
    def size(self) -> int:
        """Total number of ticks in buffer."""
        with self._lock:
            return sum(len(v) for v in self._buffer.values())
    
    def clear(self):
        """Clear all buffered ticks."""
        with self._lock:
            self._buffer.clear()


class TickProcessor:
    """
    Processes market data ticks at configurable intervals.
    
    Flow:
        WebSocket tick → TickBuffer (per symbol)
                              ↓
                    Timer fires every N seconds
                              ↓
                    Process all buffered ticks
                              ↓
                    Callback(engine, ticks)
    """
    
    def __init__(
        self,
        engine,
        tick_callback: Callable,
        interval_seconds: int = 60,
        enabled: bool = True
    ):
        self.engine = engine
        self.tick_callback = tick_callback
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        
        self._buffer = TickBuffer()
        self._running = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        self._tick_count = 0
        self._process_count = 0
    
    def on_tick(self, symbol: str, tick_data: Dict[str, Any]):
        """
        Handle incoming tick from WebSocket.
        Called by BrokerClient when new market data arrives.
        """
        if not self.enabled:
            return
        
        self._tick_count += 1
        self._buffer.add(symbol, tick_data)
        
        logger.trace(f"TickProcessor.on_tick: {symbol} added to buffer (total: {self._tick_count})")
    
    def start(self):
        """Start the tick processor background thread."""
        if not self.enabled:
            logger.info("TickProcessor disabled, skipping start")
            return
        
        if self._running.is_set():
            logger.warning("TickProcessor already running")
            return
        
        logger.info(f"🚀 Starting TickProcessor (interval: {self.interval_seconds}s)")
        self._running.set()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop the tick processor."""
        if not self._running.is_set():
            return
        
        logger.info("🛑 Stopping TickProcessor...")
        self._running.clear()
        
        if self._thread:
            self._thread.join(timeout=5)
        
        logger.info(f"🛑 TickProcessor stopped (ticks: {self._tick_count}, processes: {self._process_count})")
    
    def _run_loop(self):
        """Main processing loop."""
        logger.debug("TickProcessor loop started")
        
        while self._running.is_set():
            try:
                time.sleep(self.interval_seconds)
                
                if not self._running.is_set():
                    break
                
                self._process_buffer()
                
            except Exception as e:
                logger.error(f"TickProcessor error: {e}")
        
        logger.debug("TickProcessor loop ended")
    
    def _process_buffer(self):
        """Process all buffered ticks."""
        ticks = self._buffer.get_all_and_clear()
        
        if not ticks:
            logger.trace("TickProcessor: no ticks to process")
            return
        
        self._process_count += 1
        buffer_size = sum(len(v) for v in ticks.values())
        
        logger.info(f"🔄 TickProcessor: Processing {buffer_size} ticks from {len(ticks)} symbols (batch #{self._process_count})")
        
        try:
            self.tick_callback(self.engine, ticks)
        except Exception as e:
            logger.error(f"TickProcessor callback error: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics."""
        return {
            "enabled": self.enabled,
            "interval_seconds": self.interval_seconds,
            "ticks_received": self._tick_count,
            "batches_processed": self._process_count,
            "buffer_size": self._buffer.size()
        }
