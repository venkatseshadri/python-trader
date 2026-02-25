# orbiter/utils/constants_manager.py

import os
from typing import Dict, Any
from .data_manager import DataManager

class ConstantsManager:
    _instance = None
    _constants: Dict[str, Any] = {}

    def __new__(cls, project_root: str = None):
        if cls._instance is None:
            if project_root is None:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            cls._instance = super(ConstantsManager, cls).__new__(cls)
            cls._instance._load_constants(project_root)
        return cls._instance

    def _load_constants(self, project_root: str):
        self._constants = DataManager.load_config(project_root, 'mandatory_files', 'constants')
    
    def get(self, category: str, key: str, default: Any = None) -> Any:
        return self._constants.get(category, {}).get(key, default)

    @staticmethod
    def get_instance(project_root: str = None) -> 'ConstantsManager':
        if ConstantsManager._instance is None:
            if project_root is None:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            ConstantsManager(project_root) # Instantiate
        return ConstantsManager._instance
