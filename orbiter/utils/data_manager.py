# orbiter/utils/data_manager.py

import os
import json

class DataManager:
    """
    Centralized utility for loading and managing external data and configurations.
    This class handles all JSON interactions and path resolution via the manifest.
    """
    
    @staticmethod
    def load_json(file_path: str) -> dict:
        """Generic JSON loader with error handling."""
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ Data Error: Failed to load {file_path} - {e}")
        return {}

    @staticmethod
    def load_manifest(project_root: str) -> dict:
        """Loads the master project.json manifest."""
        return DataManager.load_json(os.path.join(project_root, 'project.json'))

    @staticmethod
    def get_manifest_path(project_root: str, category: str, item: str) -> str | None:
        """
        Resolves an absolute path for a specific item defined in the project manifest.
        Example: get_manifest_path(root, 'mandatory_files', 'system_config')
        """
        manifest = DataManager.load_manifest(project_root)
        rel_path = manifest.get(category, {}).get(item)
        if rel_path:
            return os.path.join(project_root, rel_path)
        return None

    @staticmethod
    def load_config(project_root: str, category: str, item: str) -> dict:
        """Loads a JSON configuration file defined in the manifest."""
        path = DataManager.get_manifest_path(project_root, category, item)
        if path:
            return DataManager.load_json(path)
        return {}
