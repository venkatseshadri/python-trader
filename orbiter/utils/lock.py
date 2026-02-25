# orbiter/utils/lock.py

import os
import sys
import logging
from orbiter.utils.data_manager import DataManager
from orbiter.utils.constants_manager import ConstantsManager

# Constants (will be loaded from ConstantsManager)
LOCK_ACQUIRE = "acquire"
LOCK_RELEASE = "release"

def manage_lockfile(project_root: str, action: str = LOCK_ACQUIRE) -> None:
    """
    Manage lock file using the path defined in project.json.
    Raises RuntimeError if acquisition fails.
    """
    constants = ConstantsManager.get_instance(project_root)
    manifest = DataManager.load_manifest(project_root) or {}
    lock_rel_path = manifest.get('settings', {}).get('lock_file') or constants.get('settings', 'lock_file', '.orbiter.lock')
    lock_file = os.path.join(project_root, lock_rel_path)
    
    logger = logging.getLogger(constants.get('magic_strings', 'log_name', 'ORBITER'))
    
    if action == LOCK_ACQUIRE:
        if os.path.exists(lock_file):
            try:
                with open(lock_file, 'r') as f:
                    content = f.read().strip()
                    if not content: raise ValueError("Empty lock file")
                    old_pid = int(content)
                os.kill(old_pid, 0)
                msg = constants.get('magic_strings', 'lock_collision_msg', "❌ Another instance is already running (PID: {pid}).").format(pid=old_pid)
                logger.error(msg)
                raise RuntimeError(msg)
            except (OSError, ValueError):
                try: os.remove(lock_file)
                except: pass
        
        try:
            with open(lock_file, 'w') as f:
                f.write(str(os.getpid()))
            logger.info(constants.get('magic_strings', 'lock_acquired_msg', "🔒 Lock acquired (PID: {pid}).").format(pid=os.getpid()))
        except OSError as e:
            msg = constants.get('magic_strings', 'lock_create_fail_msg', "❌ Failed to create lock file: {error}.").format(error=e)
            logger.error(msg)
            raise RuntimeError(msg)
        
    elif action == LOCK_RELEASE:
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
                logger.info(constants.get('magic_strings', 'lock_released_msg', "🔓 Lock released"))
            except OSError as e:
                msg = constants.get('magic_strings', 'lock_release_fail_msg', "⚠️ Failed to release lock: {error}").format(error=e)
                logger.warning(msg)
                raise RuntimeError(msg)
