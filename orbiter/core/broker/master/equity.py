import os
import json
import logging
import traceback
from typing import Dict
from .base import BaseParser
from orbiter.utils.data_manager import DataManager
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.meta_config_manager import MetaConfigManager

logger = logging.getLogger("ORBITER")

class EquityManager(BaseParser):
    def __init__(self, project_root: str):
        logger.debug(f"[{self.__class__.__name__}.__init__] - Initializing EquityManager.")
        self.project_root = project_root
        self.constants = ConstantsManager.get_instance(project_root)
        self.meta_config = MetaConfigManager.get_instance(project_root)
        self.project_manifest_schema = self.meta_config.get_key('project_manifest_schema')
        self.mandatory_files_key = self.project_manifest_schema.get('mandatory_files_key', 'mandatory_files')


        self.TOKEN_TO_SYMBOL: Dict[str, str] = {}
        self.SYMBOL_TO_TOKEN: Dict[str, str] = {}
        self.TOKEN_TO_COMPANY: Dict[str, str] = {}

    def load_nse_mapping(self) -> bool:
        logger.debug(f"[{self.__class__.__name__}.load_nse_mapping] - Loading NSE token mapping.")
        try:
            json_file = DataManager.get_manifest_path(self.project_root, self.mandatory_files_key, 'nse_token_map')
            
            if os.path.exists(json_file):
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    self.TOKEN_TO_SYMBOL = data[self.constants.get('magic_strings', 'token_to_symbol_key', 'token_to_symbol')]
                    self.SYMBOL_TO_TOKEN = data[self.constants.get('magic_strings', 'symbol_to_token_key', 'symbol_to_token')]
                    self.TOKEN_TO_COMPANY = data.get(self.constants.get('magic_strings', 'token_to_company_key', 'token_to_company'), {})
                logger.info(f"[{self.__class__.__name__}.load_nse_mapping] - Successfully loaded NSE token mapping from {json_file}.")
                return True
            else:
                logger.warning(f"[{self.__class__.__name__}.load_nse_mapping] - NSE token mapping file not found at {json_file}.")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}.load_nse_mapping] - Error loading NSE token mapping: {e}. Traceback: {traceback.format_exc()}")
        return False

    def save_nse_mapping(self, data: Dict):
        logger.debug(f"[{self.__class__.__name__}.save_nse_mapping] - Saving NSE token mapping.")
        try:
            cache_file = DataManager.get_manifest_path(self.project_root, self.mandatory_files_key, 'nse_token_map')
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            logger.info(f"[{self.__class__.__name__}.save_nse_mapping] - Successfully saved NSE token mapping to {cache_file}.")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}.save_nse_mapping] - Error saving NSE token mapping: {e}. Traceback: {traceback.format_exc()}")
