# orbiter/utils/data_manager.py

import os
import json

class ConfigLoader:
    """
    Loads JSON configuration files using the project manifest as a registry.
    Handles path resolution and file loading for the trading system.
    """
    
    @staticmethod
    def load_json_file(file_path: str) -> dict:
        """Load a JSON file with error handling."""
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ Data Error: Failed to load {file_path} - {e}")
        return {}

    @staticmethod
    def load_manifest(project_root: str) -> dict:
        """Load the master manifest.json registry."""
        return ConfigLoader.load_json_file(os.path.join(project_root, 'manifest.json'))

    @staticmethod
    def get_path(project_root: str, category: str, item: str) -> str | None:
        """
        Resolve an absolute path for a manifest entry.
        Example: get_path(root, 'mandatory_files', 'system_config')
        """
        manifest = ConfigLoader.load_manifest(project_root)
        rel_path = manifest.get(category, {}).get(item)
        if rel_path:
            return os.path.join(project_root, rel_path)
        return None

    @staticmethod
    def load_config(project_root: str, category: str, item: str) -> dict:
        """Load a JSON config file from the manifest."""
        path = ConfigLoader.get_path(project_root, category, item)
        if path:
            return ConfigLoader.load_json_file(path)
        return {}

    @staticmethod
    def load_json(file_path: str) -> dict:
        """Load a JSON file. Alias for load_json_file."""
        return ConfigLoader.load_json_file(file_path)

    @staticmethod
    def get_manifest_path(project_root: str, category: str, item: str) -> str | None:
        """Resolve an absolute path for a manifest entry. Alias for get_path."""
        return ConfigLoader.get_path(project_root, category, item)


class DataManager(ConfigLoader):
    """Backward compatibility - inherits all methods from ConfigLoader."""
