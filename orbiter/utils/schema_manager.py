# orbiter/utils/schema_manager.py

import os
from typing import Dict, Any
from .data_manager import DataManager

class SchemaManager:
    _instance = None
    _schema: Dict[str, Any] = {}

    def __new__(cls, project_root: str = None):
        if cls._instance is None:
            if project_root is None:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            cls._instance = super(SchemaManager, cls).__new__(cls)
            cls._instance._load_schema(project_root)
        return cls._instance

    def _load_schema(self, project_root: str):
        self._schema = DataManager.load_config(project_root, 'mandatory_files', 'schema')
    
    def get_key(self, schema_name: str, key_name: str | None = None, default: Any = None) -> Any:
        """
        Retrieves a dynamic key name from the schema.
        Example: schema_manager.get_key('rule_schema', 'rules_key') -> 'rules'
        If key_name is None, returns the entire schema section.
        """
        if key_name is None:
            return self._schema.get(schema_name, default)
        return self._schema.get(schema_name, {}).get(key_name, default)

    @staticmethod
    def get_instance(project_root: str = None) -> 'SchemaManager':
        if SchemaManager._instance is None:
            if project_root is None:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            SchemaManager(project_root) # Instantiate
        return SchemaManager._instance
