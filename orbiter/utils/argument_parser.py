# orbiter/utils/argument_parser.py

import os
import json
import logging

class ArgumentParser:
    """
    Utility for parsing command-line arguments into generic facts for the rules engine.
    Supports both --strategyId=full_name and --strategyCode=N (short code).
    Supports dynamic strategy selection via --strategyExecution=dynamic.
    """
    
    @staticmethod
    def _load_strategy_codes(project_root: str = None) -> dict:
        """Load strategy code mappings from config.json"""
        if not project_root:
            return {}
        config_json_path = os.path.join(project_root, "orbiter", "config", "config.json")
        if os.path.exists(config_json_path):
            try:
                with open(config_json_path, 'r') as f:
                    config = json.load(f)
                    return config.get('strategy_codes', {})
            except Exception:
                pass
        return {}

    @staticmethod
    def _load_dynamic_strategy_config(project_root: str = None) -> dict:
        """Load dynamic strategy rules from config file"""
        if not project_root:
            return {}
        config_path = os.path.join(project_root, "orbiter", "config", "dynamic_strategy_rules.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    @staticmethod
    def _resolve_strategy(code_or_id: str, project_root: str = None) -> str:
        """
        Resolve strategy code (e.g., '1') to strategyId, or return as-is if not a code.
        """
        if not code_or_id:
            return None
        
        strategy_codes = ArgumentParser._load_strategy_codes(project_root)
        
        # Check if it's a known code
        if code_or_id in strategy_codes:
            resolved = strategy_codes[code_or_id]
            logging.getLogger(__name__).info(f"Resolved strategy code '{code_or_id}' -> '{resolved}'")
            return resolved
        
        # Not a code, return as-is (full strategyId)
        return code_or_id

    @staticmethod
    def parse_cli_to_facts(args_list: list, project_root: str = None) -> dict:
        """
        Turns list of CLI args into facts dict.
        
        Examples:
        - ['--strategyCode=m1'] -> {paper_trade: True, strategyid: 'mcx_trend_follower', strategy_execution: 'fixed'}
        - ['--real_broker_trade=true', '--strategyCode=m1'] -> {paper_trade: False, strategyid: 'mcx_trend_follower'}
        - ['--strategyExecution=dynamic'] -> {paper_trade: True, strategy_execution: 'dynamic'}
        
        Raises:
            ValueError: If both --strategyExecution=dynamic and --strategyCode/--strategyId are provided
        """
        logger = logging.getLogger(__name__)
        facts = {
            'paper_trade': True,  # Default to paper trade for safety
            'real_broker_trade': False,  # Default to paper trading
            'simulation': True,
            'strategy_execution': 'fixed',
            'mock_data': False,
            'mock_data_file': None
        }
        
        parsed_strategy_input = None
        use_strategy_code = False
        strategy_execution = 'fixed'
        paper_trade_set = False
        real_broker_trade_set = False
        
        # Known arguments - process these, but still pass through unknown args
        # Use kebab-case in CLI, convert to snake_case internally
        known_args = {'real_broker_trade', 'strategy_id', 'strategyid', 'strategy_code', 'strategy_execution', 'strategycode', 'strategyexecution', 'mock_data', 'mock_data_file', 'clear_paper_positions'}
        
        # Process only first 5 arguments (to maintain backward compatibility)
        for arg in args_list[:5]:
            if arg.startswith("--"):
                clean = arg.lstrip("-")
                if "=" in clean:
                    k, v = clean.split("=", 1)
                    k_clean = k.lower().replace("-", "_")
                    v_clean = v.lower()
                    
                    # Always pass through to facts
                    if v_clean == 'true':
                        facts[k_clean] = True
                    elif v_clean == 'false':
                        facts[k_clean] = False
                    else:
                        facts[k_clean] = v
                    
                    # Only process known args for logic
                    if k_clean in known_args:
                        if k_clean in ('strategy_id', 'strategyid', 'strategycode'):
                            parsed_strategy_input = v
                        elif k_clean in ('strategy_code',):
                            parsed_strategy_input = v
                            use_strategy_code = True
                        elif k_clean in ('strategy_execution', 'strategyexecution'):
                            strategy_execution = v
                        elif k_clean == 'real_broker_trade':
                            real_broker_trade_set = True
                            if v_clean == 'true':
                                facts['paper_trade'] = False
                                facts['real_broker_trade'] = True
                                paper_trade_set = True
                            else:
                                facts['real_broker_trade'] = False
                        elif k_clean == 'mock_data_file':
                            facts['mock_data_file'] = v
                else:
                    k_clean = clean.lower().replace("-", "_")
                    facts[k_clean] = True
                    if k_clean == 'real_broker_trade':
                        real_broker_trade_set = True
                        facts['paper_trade'] = False
                        facts['real_broker_trade'] = True
                        paper_trade_set = True
        
        # Set defaults based on flags
        if not paper_trade_set:
            facts['paper_trade'] = True
        
        # Handle dynamic vs fixed mode
        if strategy_execution == 'dynamic':
            if parsed_strategy_input:
                raise ValueError(
                    f"Conflict: Cannot use --strategyExecution=dynamic with --strategyCode or --strategyId. "
                    f"Use one or the other."
                )
            
            dynamic_config = ArgumentParser._load_dynamic_strategy_config(project_root)
            
            if not dynamic_config or not dynamic_config.get('enabled', False):
                logger.warning("Dynamic strategy selection enabled but config not found or disabled. Falling back to fixed.")
                facts['strategy_execution'] = 'fixed'
            else:
                facts['strategy_execution'] = 'dynamic'
                facts['dynamic_strategy_config'] = dynamic_config
                facts['check_time'] = dynamic_config.get('check_time', '10:00')
                logger.info(f"Dynamic strategy selection enabled. Will evaluate at {facts['check_time']}")
        else:
            facts['strategy_execution'] = 'fixed'
            
            resolved_strategy_input = None
            if parsed_strategy_input:
                resolved_strategy_input = ArgumentParser._resolve_strategy(parsed_strategy_input, project_root)
            
            final_strategy_id = 'default'
            system_default_strategy = None
            
            if project_root:
                config_json_path = os.path.join(project_root, "orbiter", "config", "config.json")
                if os.path.exists(config_json_path):
                    try:
                        with open(config_json_path, 'r') as f:
                            config = json.load(f)
                            system_default_strategy = config.get('default_strategy')
                    except Exception as e:
                        logger.error(f"Failed to read {config_json_path}: {e}")

            if resolved_strategy_input and project_root:
                strat_dir = os.path.join(project_root, "orbiter", "strategies", resolved_strategy_input)
                if not os.path.exists(strat_dir) or not os.path.isdir(strat_dir):
                    logger.warning(f"Strategy '{resolved_strategy_input}' not found at {strat_dir}. Falling back to default.")
                    resolved_strategy_input = None

            if resolved_strategy_input:
                final_strategy_id = resolved_strategy_input
            elif system_default_strategy:
                sys_strat_dir = os.path.join(project_root, "orbiter", "strategies", system_default_strategy) if project_root else None
                if sys_strat_dir and (not os.path.exists(sys_strat_dir) or not os.path.isdir(sys_strat_dir)):
                     logger.warning(f"System default strategy '{system_default_strategy}' not found. Falling back to 'default'.")
                else:
                     final_strategy_id = system_default_strategy
            else:
                logger.warning("No valid strategyId provided or found in config.json. Falling back to 'default'.")

            facts['strategyid'] = final_strategy_id
            facts['strategy_input'] = parsed_strategy_input
            facts['using_strategy_code'] = use_strategy_code
                    
        return facts
