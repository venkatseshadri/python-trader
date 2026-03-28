import os
import fcntl
import pathlib
from .logger import setup_logging

LOCK_ACQUIRE = "acquire"
LOCK_RELEASE = "release"

def manage_lockfile(project_root: str, action: str, logger=None):
    """
    Manages the application-wide lockfile to prevent multiple Orbiter instances from running.
    """
    lockfile_path = pathlib.Path(project_root) / "orbiter.lock"
    
    if logger is None:
        logger = setup_logging()

    if action == LOCK_ACQUIRE:
        try:
            lockfile_path.touch(exist_ok=False)
            _lock_file = open(lockfile_path, "r+")
            fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            setattr(manage_lockfile, '_lock_file', _lock_file)
            logger.info(f"✅ Lock acquired: {lockfile_path}")
        except FileExistsError:
            logger.critical(f"❌ Another Orbiter instance is running. Lockfile: {lockfile_path}")
            raise RuntimeError("Another Orbiter instance is already running.")
        except IOError as e:
            logger.critical(f"❌ Failed to acquire lock: {e}")
            raise RuntimeError("Failed to acquire application lock.")
    elif action == LOCK_RELEASE:
        if hasattr(manage_lockfile, '_lock_file'):
            fcntl.flock(getattr(manage_lockfile, '_lock_file'), fcntl.LOCK_UN)
            getattr(manage_lockfile, '_lock_file').close()
            delattr(manage_lockfile, '_lock_file')
        
        if lockfile_path.exists():
            os.remove(lockfile_path)
            logger.info(f"🗑️ Lock released: {lockfile_path}")
        else:
            logger.warning(f"⚠️ Lockfile not found during release: {lockfile_path}")