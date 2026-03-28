# orbiter/utils/data_manager.py

import os
import json
import logging

logger = logging.getLogger(__name__)

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
                logger.error(f"Failed to load {file_path}: {e}")
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
            path = os.path.join(project_root, rel_path)
            logger.debug(f"Resolved path [{category}][{item}]: {path}")
            return path
        logger.warning(f"Manifest key not found: [{category}][{item}]")
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

    @staticmethod
    def validate_manifest(project_root: str, fail_on_missing_optional: bool = False) -> dict:
        """
        Validate that all files listed in manifest exist.
        
        Args:
            project_root: Root directory of the project
            fail_on_missing_optional: If True, fail on missing optional files too
            
        Returns:
            dict with 'valid', 'mandatory_missing', 'optional_missing', 'all_files'
        """
        manifest = ConfigLoader.load_manifest(project_root)
        
        result = {
            'valid': True,
            'mandatory_missing': [],
            'optional_missing': [],
            'all_files': []
        }
        
        # Validate mandatory files
        mandatory = manifest.get('mandatory_files', {})
        for name, rel_path in mandatory.items():
            abs_path = os.path.join(project_root, rel_path)
            result['all_files'].append({'name': name, 'path': abs_path, 'mandatory': True})
            if not os.path.exists(abs_path):
                result['mandatory_missing'].append(rel_path)
                result['valid'] = False
                logger.error(f"❌ MISSING mandatory file: {rel_path}")
        
        # Validate optional files
        optional = manifest.get('optional_files', {})
        for name, rel_path in optional.items():
            abs_path = os.path.join(project_root, rel_path)
            result['all_files'].append({'name': name, 'path': abs_path, 'mandatory': False})
            if not os.path.exists(abs_path):
                result['optional_missing'].append(rel_path)
                if fail_on_missing_optional:
                    result['valid'] = False
                    logger.warning(f"❌ MISSING optional file: {rel_path}")
                else:
                    logger.debug(f"⚪ Optional file not found: {rel_path}")
        
        # Validate structure paths exist
        structure = manifest.get('structure', {})
        for name, rel_path in structure.items():
            abs_path = os.path.join(project_root, rel_path)
            if not os.path.exists(abs_path):
                logger.warning(f"⚠️ Structure path missing: [{name}] = {rel_path}")
        
        # Log summary
        if result['valid']:
            logger.info(f"✅ Manifest validation passed ({len(mandatory)} mandatory, {len(optional)} optional)")
        else:
            logger.error(f"❌ Manifest validation FAILED - {len(result['mandatory_missing'])} missing")
        
        return result