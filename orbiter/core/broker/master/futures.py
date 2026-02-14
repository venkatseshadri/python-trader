import os
import json
from typing import List, Dict, Any
from .base import BaseParser

class FuturesManager(BaseParser):
    def __init__(self):
        self.DATA: List[Dict[str, Any]] = []

    def _get_path(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        return os.path.join(base_dir, 'data', 'futures_master.json')

    def load_cache(self):
        path = self._get_path()
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    self.DATA = json.load(f)
                    return True
            except Exception: pass
        return False

    def save_cache(self):
        path = self._get_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.DATA, f)

    def add_entries(self, rows: List[Dict[str, Any]]):
        self.DATA.extend(rows)
        self.save_cache()
