# orbiter/core/ancillary_service.py

import logging
import threading
from abc import ABC, abstractmethod

logger = logging.getLogger("ORBITER")


class AncillaryService(ABC):
    """Base class for background services (reporting, monitoring, etc.)."""
    
    def __init__(self, app):
        self.app = app
        self._running = threading.Event()
        self._thread = None
    
    @abstractmethod
    def name(self) -> str:
        """Service name for logging."""
        pass
    
    @abstractmethod
    def _run_loop(self):
        """Main service loop. Override with implementation."""
        pass
    
    def start(self):
        """Start the service in a background thread."""
        if self._running.is_set():
            logger.warning(f"{self.name()} already running")
            return
        
        self._running.set()
        self._thread = threading.Thread(target=self._service_wrapper, daemon=True)
        self._thread.start()
        logger.info(f"🚀 {self.name()} started")
    
    def _service_wrapper(self):
        """Wrapper that runs the service loop with error handling."""
        while self._running.is_set():
            try:
                self._run_loop()
            except Exception as e:
                logger.error(f"❌ {self.name()} error: {e}")
    
    def stop(self):
        """Stop the service."""
        if not self._running.is_set():
            return
        
        logger.info(f"🛑 {self.name()} stopping...")
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info(f"🛑 {self.name()} stopped")


class AncillaryServiceManager:
    """Manages all ancillary services."""
    
    def __init__(self, app):
        self.app = app
        self._services = {}
    
    def register(self, service: AncillaryService):
        """Register a service."""
        self._services[service.name()] = service
        logger.debug(f"Registered service: {service.name()}")
    
    def start_all(self):
        """Start all registered services."""
        for service in self._services.values():
            service.start()
    
    def stop_all(self):
        """Stop all registered services."""
        for service in self._services.values():
            service.stop()
    
    def get(self, name: str) -> AncillaryService:
        """Get a service by name."""
        return self._services.get(name)
