# orbiter/utils/logger.py

import os
import sys
import logging
from datetime import datetime
from orbiter.utils.system import get_manifest, get_constants

# Define custom TRACE level
TRACE_LEVEL_NUM = 5  # Below DEBUG (10)
logging.addLevelName(TRACE_LEVEL_NUM, 'TRACE')

LOG_LEVELS = {
    "TRACE": TRACE_LEVEL_NUM,
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}

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
    def flush(self):
        pass

def _get(d: dict, category: str, key: str, default=None):
    """Helper to get nested dict value."""
    return d.get(category, {}).get(key, default)

def setup_logging(project_root: str, log_level: str = "INFO") -> logging.Logger:
    """Setup dual logging with paths from manifest.json and configurable level."""
    # CRITICAL: Disable "Logging error" messages BEFORE any logging setup
    logging.raiseExceptions = False
    
    manifest = get_manifest()
    constants = get_constants()
    
    log_rel_path = manifest.get('structure', {}).get('logs', 'logs/system')
    log_dir = os.path.join(project_root, log_rel_path)
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_name = _get(constants, 'magicStrings', 'log_name', 'ORBITER')
    log_file = os.path.join(log_dir, f"{log_name.lower()}_{timestamp}.log")

    # Convert string log level to logging module constant
    numeric_level = LOG_LEVELS.get(log_level.upper(), logging.INFO)

    # Set external API loggers to same level
    for logger_name in ("NorenRestApiPy", "urllib3", "websocket", "websockets"):
        logging.getLogger(logger_name).setLevel(numeric_level)

    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    l = logging.getLogger(log_name)
    l.setLevel(numeric_level)  # Explicitly set logger level (not just effective level)
    sys.stdout = LoggerWriter(l.info, raw=True)
    sys.stderr = LoggerWriter(l.error)
    # Skip - init message handled separately, or set a marker
    return l
