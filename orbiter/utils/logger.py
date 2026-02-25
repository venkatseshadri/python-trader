# orbiter/utils/logger.py

import os
import sys
import logging
from datetime import datetime
from orbiter.utils.data_manager import DataManager
from orbiter.utils.constants_manager import ConstantsManager

# Define custom TRACE level
TRACE_LEVEL_NUM = 5  # Below DEBUG (10)
logging.addLevelName(TRACE_LEVEL_NUM, 'TRACE')

def trace(self, message, *args, **kws):
    if self.isEnabledFor(TRACE_LEVEL_NUM):
        self._log(TRACE_LEVEL_NUM, message, args, **kws)

logging.Logger.trace = trace

class LoggerWriter:
    """Helper class to redirect stdout/stderr to a logger."""
    def __init__(self, level, raw=False):
        self.level = level
        self.raw = raw
    def write(self, message):
        if message and message.strip():
            self.level(message.strip())
            if self.raw:
                sys.__stdout__.write(message)
    def flush(self):
        pass

def setup_logging(project_root: str, log_level: str = "INFO") -> logging.Logger:
    """Setup dual logging with paths from project.json and configurable level."""
    constants = ConstantsManager.get_instance()
    manifest = DataManager.load_manifest(project_root) # Make sure manifest is loaded
    log_rel_path = manifest.get('structure', {}).get('logs', 'logs/system') # Default to a string literal fallback for robustness
    
    log_dir = os.path.join(project_root, log_rel_path)
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{constants.get('magic_strings', 'log_name', 'ORBITER').lower()}_{timestamp}.log")
    
    logger_name = constants.get('magic_strings', 'log_name', 'ORBITER')

    # Convert string log level to logging module constant
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        # Fallback for custom TRACE level
        if log_level.upper() == 'TRACE':
            numeric_level = TRACE_LEVEL_NUM
        else:
            numeric_level = logging.INFO # Default to INFO if invalid

    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    l = logging.getLogger(logger_name)
    sys.stdout = LoggerWriter(l.info, raw=True)
    sys.stderr = LoggerWriter(l.error)
    l.info(f"Logging initialized to level: {log_level.upper()}")
    return l
