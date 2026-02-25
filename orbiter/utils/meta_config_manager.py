import os
from typing import Dict, Any


class MetaConfigManager:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls, project_root: str = None):
        if cls._instance is None:
            cls._instance = super(MetaConfigManager, cls).__new__(cls)
            cls._instance._load_defaults()
        return cls._instance

    def _load_defaults(self):
        # Minimal defaults to keep refactored components functional.
        self._config = {
            "project_manifest_schema": {
                "structure_key": "structure",
                "mandatory_files_key": "mandatory_files",
                "settings_key": "settings",
            },
            "global_config_schema": {
                "trade_score_key": "trade_score",
                "log_level_key": "log_level",
            },
            "ghost_template_file_schema": {
                "default_template_key": "default_ghost_position_template",
                "strategy_derivation_key": "strategy_derivation",
                "conditions_key": "conditions",
                "actions_key": "actions",
            },
            "rule_file_schema": {
                "fact_key": "fact",
                "operator_key": "operator",
                "value_key": "value",
                "all_of_key": "allOf",
                "any_of_key": "anyOf",
                "conditions_key": "conditions",
                "actions_key": "actions",
            },
            "broker_data_mapping_schema": {
                "data_points_key": "data_points",
                "broker_key": "broker_key",
                "system_key": "system_key",
            },
        }

    def get_key(self, schema_name: str, key_name: str = None, default: Any = None) -> Any:
        if key_name is None:
            return self._config.get(schema_name, default)
        return self._config.get(schema_name, {}).get(key_name, default)

    @staticmethod
    def get_instance(project_root: str = None) -> 'MetaConfigManager':
        if MetaConfigManager._instance is None:
            MetaConfigManager(project_root)
        return MetaConfigManager._instance

