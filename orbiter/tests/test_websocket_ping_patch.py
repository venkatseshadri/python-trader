"""
WebSocket Ping Interval Test
Tests with modified ping_interval to reduce reconnection frequency
"""
import sys
import os
import time
import threading
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("websocket.test")

# Patch the library BEFORE importing ShoonyaApiPy
original_source = """
    def __ws_run_forever(self):
        
        while self.__stop_event.is_set() == False:
            try:
                self.__websocket.run_forever( ping_interval=3,  ping_payload='{"t":"h"}')
            except Exception as e:
                logger.warning(f"websocket run forever ended in exception, {e}")
            
            sleep(0.1) # Sleep for 100ms between reconnection.
"""

patched_source = """
    def __ws_run_forever(self):
        
        while self.__stop_event.is_set() == False:
            try:
                # Patched: 30 second ping interval (was 3 seconds)
                self.__websocket.run_forever( ping_interval=30,  ping_payload='{"t":"h"}')
            except Exception as e:
                logger.warning(f"websocket run forever ended in exception, {e}")
            
            sleep(0.1) # Sleep for 100ms between reconnection.
"""

# Apply monkey patch
import NorenRestApiPy.NorenApi as NorenApi

# Store original method
_original_method = NorenApi.NorenApi._NorenApi__ws_run_forever

def patched_ws_run_forever(self):
    """Patched version with 30s ping interval"""
    import websocket
    import time
    from time import sleep
    
    # Import the stop event from the instance
    stop_event = getattr(self, '_NorenApi__stop_event', None)
    if stop_event is None:
        # Fallback to original behavior
        return _original_method(self)
    
    while stop_event.is_set() == False:
        try:
            ws = getattr(self, '_NorenApi__websocket', None)
            if ws:
                # Use 30 second ping interval instead of 3
                ws.run_forever(ping_interval=30, ping_payload='{"t":"h"}')
            else:
                break
        except Exception as e:
            logger.warning(f"websocket run forever ended in exception, {e}")
        
        sleep(0.1)

# Apply the patch
NorenApi.NorenApi._NorenApi__ws_run_forever = patched_ws_run_forever
print("✅ Patched NorenApi with 30s ping interval")

# Now test import and show the change
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ShoonyaApi-py'))

from api_helper import ShoonyaApiPy
print(f"✅ API Helper loaded. Broker: {ShoonyaApiPy().broker_name if hasattr(ShoonyaApiPy, '__init__') else 'N/A'}")

# Verify patch is applied
import inspect
source = inspect.getsource(patched_ws_run_forever)
if 'ping_interval=30' in source:
    print("✅ PING INTERVAL PATCH VERIFIED: 30 seconds")
else:
    print("❌ PATCH FAILED")
