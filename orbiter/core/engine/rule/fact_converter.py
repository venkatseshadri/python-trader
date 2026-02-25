# orbiter/core/engine/rule/fact_converter.py

import logging
import numpy as np
from typing import Dict, Any, List
from orbiter.utils.data_manager import DataManager
from orbiter.utils.utils import safe_float
from orbiter.utils.meta_config_manager import MetaConfigManager

logger = logging.getLogger("ORBITER")

class FactConverter:
    """
    Converts raw broker candle data into a standardized format (NumPy arrays)
    for use by the FactCalculator. It uses a configurable mapping to
    translate broker-specific keys to generic ones.
    """
    def __init__(self, project_root: str):
        logger.debug(f"[{self.__class__.__name__}.__init__] - Initializing FactConverter.")
        self.meta_config = MetaConfigManager.get_instance(project_root)
        self.broker_data_map_schema = self.meta_config.get_key('broker_data_mapping_schema')
        self.broker_data_mapping = DataManager.load_config(project_root, 'mandatory_files', 'broker_data_mapping')
        logger.debug(f"[{self.__class__.__name__}.__init__] - Broker data mapping loaded: {self.broker_data_mapping}")


    def convert_candle_data(self, raw_candle_data: List[Dict]) -> Dict[str, np.ndarray]:
        """
        Converts a list of raw broker candle dictionaries into a dictionary
        of standardized NumPy arrays (e.g., 'close': np.array([...])).
        """
        logger.debug(f"[{self.__class__.__name__}.convert_candle_data] - Converting {len(raw_candle_data)} raw candle data points.")
        standardized_data = {
            'close': [], 'high': [], 'low': [], 'open': [], 'volume': []
        }
        
        candle_data_mapping_key = self.broker_data_map_schema.get('candle_data_mapping_key', 'candle_data_mapping')
        mapping = self.broker_data_mapping.get(candle_data_mapping_key, {})

        close_key_broker = mapping.get('close_key', 'intc')
        high_key_broker = mapping.get('high_key', 'inth')
        low_key_broker = mapping.get('low_key', 'intl')
        open_key_broker = mapping.get('open_key', 'into')
        volume_key_broker = mapping.get('volume_key', 'v')
        status_key_broker = mapping.get('status_key', 'stat')

        logger.trace(f"[{self.__class__.__name__}.convert_candle_data] - Using broker keys: Close={close_key_broker}, High={high_key_broker}, Low={low_key_broker}, Open={open_key_broker}, Volume={volume_key_broker}, Status={status_key_broker}")

        for candle in raw_candle_data:
            logger.trace(f"[{self.__class__.__name__}.convert_candle_data] - Processing raw candle: {candle}")
            if candle.get(status_key_broker) == 'Ok':
                standardized_data['close'].append(safe_float(candle.get(close_key_broker)))
                standardized_data['high'].append(safe_float(candle.get(high_key_broker)))
                standardized_data['low'].append(safe_float(candle.get(low_key_broker)))
                standardized_data['open'].append(safe_float(candle.get(open_key_broker)))
                standardized_data['volume'].append(safe_float(candle.get(volume_key_broker)))
            else:
                logger.trace(f"[{self.__class__.__name__}.convert_candle_data] - Skipping candle due to status: {candle.get(status_key_broker)}")
        
        for key, value_list in standardized_data.items():
            standardized_data[key] = np.array(value_list, dtype=float)
            logger.trace(f"[{self.__class__.__name__}.convert_candle_data] - Converted '{key}' to numpy array: {standardized_data[key][:5]}...") # Log first 5 elements

        logger.debug(f"[{self.__class__.__name__}.convert_candle_data] - Finished converting candle data.")
        return standardized_data
