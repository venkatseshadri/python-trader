import os
import json
import logging
import traceback
from typing import List, Dict, Any
from .base import BaseParser
from orbiter.utils.data_manager import DataManager
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.meta_config_manager import MetaConfigManager

logger = logging.getLogger("ORBITER")

class FuturesManager(BaseParser):
    def __init__(self, project_root: str):
        logger.debug(f"[{self.__class__.__name__}.__init__] - Initializing FuturesManager.")
        self.project_root = project_root
        self.constants = ConstantsManager.get_instance(project_root)
        self.meta_config = MetaConfigManager.get_instance(project_root)
        self.project_manifest_schema = self.meta_config.get_key('project_manifest_schema')
        self.mandatory_files_key = self.project_manifest_schema.get('mandatory_files_key', 'mandatory_files')

        self.DATA: List[Dict[str, Any]] = []

    def _get_path(self):
        futures_master_file_key = self.constants.get('magic_strings', 'futures_master_file_key', 'futures_master_file')
        return DataManager.get_manifest_path(self.project_root, self.mandatory_files_key, futures_master_file_key)

    def load_cache(self):
        path = self._get_path()
        logger.debug(f"[{self.__class__.__name__}.load_cache] - Loading futures master cache from: {path}")
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    self.DATA = json.load(f)
                    logger.info(f"[{self.__class__.__name__}.load_cache] - Successfully loaded futures master cache.")
                    return True
            except Exception as e:
                logger.error(f"[{self.__class__.__name__}.load_cache] - Error loading futures master cache from {path}: {e}. Traceback: {traceback.format_exc()}")
        else:
            logger.debug(f"[{self.__class__.__name__}.load_cache] - Futures master cache file not found at {path}.")
        return False

    def save_cache(self):
        path = self._get_path()
        logger.debug(f"[{self.__class__.__name__}.save_cache] - Saving futures master cache to: {path}")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump(self.DATA, f)
            logger.info(f"[{self.__class__.__name__}.save_cache] - Successfully saved futures master cache.")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}.save_cache] - Error saving futures master cache to {path}: {e}. Traceback: {traceback.format_exc()}")

    def add_entries(self, rows: List[Dict[str, Any]]):
        logger.debug(f"[{self.__class__.__name__}.add_entries] - Adding {len(rows)} entries to futures master.")
        self.DATA.extend(rows)
        self.save_cache()
