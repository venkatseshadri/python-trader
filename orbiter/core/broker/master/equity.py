import os
import json
from typing import Dict
from .base import BaseParser

class EquityManager(BaseParser):
    def __init__(self):
        self.TOKEN_TO_SYMBOL: Dict[str, str] = {}
        self.SYMBOL_TO_TOKEN: Dict[str, str] = {}
        self.TOKEN_TO_COMPANY: Dict[str, str] = {}

    def load_nse_mapping(self) -> bool:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        json_file = os.path.join(base_dir, 'data', 'nse_token_map.json')
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    self.TOKEN_TO_SYMBOL = data['token_to_symbol']
                    self.SYMBOL_TO_TOKEN = data['symbol_to_token']
                    self.TOKEN_TO_COMPANY = data.get('token_to_company', {})
                return True
            except Exception: pass
        return False

    def save_nse_mapping(self, data: Dict):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        cache_file = os.path.join(base_dir, 'data', 'nse_token_map.json')
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(data, f)
