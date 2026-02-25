# orbiter/utils/argument_parser.py

import os
import json
import logging

class ArgumentParser:
    """
    Utility for parsing command-line arguments into generic facts for the rules engine.
    """
    
    @staticmethod
    def parse_cli_to_facts(args_list: list, project_root: str = None) -> dict:
        """
        Turns list of CLI args like ['--simulation=true', '--strategyId=strat1'] into { 'simulation': True, 'strategyid': 'strat1' }.
        Defaults to simulation=True and strategyid from system.json if missing.
        Ignores any arguments beyond the first two.
        Validates if strategy directory exists, falling back to system.json default if invalid.
        """
        logger = logging.getLogger(__name__)
        facts = {
            'simulation': True
        }
        
        parsed_strategy_id = None
        
        # Only process up to 2 arguments
        for arg in args_list[:2]:
            if arg.startswith("--"):
                clean = arg.lstrip("-")
                if "=" in clean:
                    k, v = clean.split("=", 1)
                    k_clean = k.lower().replace("-", "_")
                    v_clean = v.lower()
                    
                    if v_clean == 'true':
                        facts[k_clean] = True
                    elif v_clean == 'false':
                        facts[k_clean] = False
                    else:
                        facts[k_clean] = v
                        if k_clean == 'strategyid':
                            parsed_strategy_id = v
                else:
                    # Treat as boolean flag
                    k_clean = clean.lower().replace("-", "_")
                    facts[k_clean] = True
                    
        # Determine strategyId and validate
        final_strategy_id = 'default'
        system_default_strategy = None
        
        if project_root:
            system_json_path = os.path.join(project_root, "orbiter", "config", "system.json")
            if os.path.exists(system_json_path):
                try:
                    with open(system_json_path, 'r') as f:
                        system_config = json.load(f)
                        system_default_strategy = system_config.get('strategyId')
                except Exception as e:
                    logger.error(f"Failed to read {system_json_path}: {e}")

        # Check if provided strategy exists
        if parsed_strategy_id and project_root:
            strat_dir = os.path.join(project_root, "orbiter", "strategies", parsed_strategy_id)
            if not os.path.exists(strat_dir) or not os.path.isdir(strat_dir):
                logger.warning(f"Strategy '{parsed_strategy_id}' not found at {strat_dir}. Falling back to default.")
                parsed_strategy_id = None

        if parsed_strategy_id:
            final_strategy_id = parsed_strategy_id
        elif system_default_strategy:
            if not parsed_strategy_id and 'strategyid' not in [k.lower().replace("-", "_") for k in (arg.split("=")[0].lstrip("-") for arg in args_list[:2] if arg.startswith("--"))]:
                 # Don't log warning if they just omitted it, since we have a system default
                 pass
            
            # validate system default
            sys_strat_dir = os.path.join(project_root, "orbiter", "strategies", system_default_strategy) if project_root else None
            if sys_strat_dir and (not os.path.exists(sys_strat_dir) or not os.path.isdir(sys_strat_dir)):
                 logger.warning(f"System default strategy '{system_default_strategy}' not found at {sys_strat_dir}. Falling back to 'default'.")
            else:
                 final_strategy_id = system_default_strategy
        else:
            logger.warning("No valid strategyId provided or found in system.json. Falling back to 'default'.")

        facts['strategyid'] = final_strategy_id
                    
        return facts
