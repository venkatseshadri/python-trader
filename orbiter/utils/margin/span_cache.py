# orbiter/utils/margin/span_cache.py
"""
Span Cache - handles caching of span calculations to avoid repeated API calls.
"""

import json
import os
import logging
from typing import Dict, Optional


class SpanCache:
    """Manages span calculation cache."""
    
    def __init__(self, cache_path: str = None):
        self.cache_path = cache_path
        self._cache: Dict = {}
        self.logger = logging.getLogger("span_cache")
    
    @property
    def cache(self) -> Dict:
        """Get the cache dictionary."""
        return self._cache if self._cache is not None else {}
    
    def set_cache_path(self, path: str):
        """Set the cache file path."""
        self.logger.debug(f"[SpanCache] Setting cache path to: {path}")
        self.cache_path = path
    
    def load(self) -> Dict:
        """Load span cache from file."""
        self.logger.debug(f"[SpanCache] Loading span cache from: {self.cache_path}")
        
        if not self.cache_path:
            self.logger.debug("[SpanCache] Cache path not set.")
            return {}
        
        if not os.path.exists(self.cache_path):
            self.logger.debug("[SpanCache] Cache file not found, initializing empty cache.")
            self._cache = {}
            return {}
        
        try:
            with open(self.cache_path, 'r') as f:
                self._cache = json.load(f)
            self.logger.debug("[SpanCache] Span cache loaded successfully.")
            return self._cache
        except Exception as e:
            self.logger.error(f"[SpanCache] Failed to load span cache: {e}")
            self._cache = {}
            return {}
    
    def save(self):
        """Save span cache to file."""
        self.logger.debug(f"[SpanCache] Saving span cache to: {self.cache_path}")
        
        if not self.cache_path or self._cache is None:
            self.logger.debug("[SpanCache] Cache path not set or cache is empty. Skipping save.")
            return
        
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, 'w') as f:
                json.dump(self._cache, f)
            self.logger.debug("[SpanCache] Span cache saved successfully.")
        except Exception as e:
            self.logger.error(f"[SpanCache] Failed to save span cache: {e}")
    
    def get(self, key: str) -> Optional[Dict]:
        """Get a cached span calculation."""
        return self._cache.get(key)
    
    def set(self, key: str, value: Dict):
        """Set a cached span calculation."""
        self._cache[key] = value
    
    def clear(self):
        """Clear the cache."""
        self._cache = {}
