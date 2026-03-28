# orbiter/utils/schema_manager.py

import os
import sys
from typing import Dict, Any
from .data_manager import DataManager

class SchemaManager:
    _instance = None
    _schema: Dict[str, Any] = {}
    _project_root: str = None

    def __new__(cls, project_root: str = None):
        # Always reinitialize if a different project_root is provided
        if cls._instance is None or (project_root is not None and cls._instance._project_root != project_root):
            if project_root is None:
                # Check if running as PyInstaller
                if getattr(sys, 'frozen', False):
                    # Use executable dir, not _MEIPASS (which is a temp dir)
                    executable_dir = os.path.dirname(sys.executable)
                    project_root = os.path.dirname(executable_dir)
                else:
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            cls._instance = super(SchemaManager, cls).__new__(cls)
            cls._instance._project_root = project_root
            cls._instance._load_schema(project_root)
        return cls._instance

    def _load_schema(self, project_root: str):
        schema_path = os.path.join(project_root, 'orbiter', 'config', 'schema.json')
        self._schema = DataManager.load_json(schema_path)
        self._project_root = project_root
    
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
        # Always reinitialize if project_root is provided to ensure correct schema
        if SchemaManager._instance is None or project_root is not None:
            if project_root is None:
                # Check if running as PyInstaller
                if getattr(sys, 'frozen', False):
                    # Use executable dir, not _MEIPASS
                    executable_dir = os.path.dirname(sys.executable)
                    project_root = os.path.dirname(executable_dir)
                else:
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            SchemaManager(project_root)
        return SchemaManager._instance
    
    @staticmethod
    def reset():
        """Reset singleton - useful for testing"""
        SchemaManager._instance = None
        SchemaManager._schema = {}
        SchemaManager._project_root = None