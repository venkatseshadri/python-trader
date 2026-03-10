# orbiter/utils/constants_manager.py

from typing import Any
from . import system

class ConstantsManager:
    _instance: 'ConstantsManager | None' = None

    def __init__(self):
        if ConstantsManager._instance is None:
            ConstantsManager._instance = self

    def get(self, category: str, key: str, default: Any = None) -> Any:
        return system.CONSTANTS.get(category, {}).get(key, default)

    @classmethod
    def get_instance(cls) -> 'ConstantsManager':
        if cls._instance is None:
            cls()
        return cls._instance  # type: ignore
