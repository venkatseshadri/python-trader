import os
import fcntl
import pathlib

LOCK_ACQUIRE = "acquire"
LOCK_RELEASE = "release"

def manage_lockfile(project_root: str, action: str):
    """
    Manages the application-wide lockfile to prevent multiple Orbiter instances from running.
    """
    lockfile_path = pathlib.Path(project_root) / "orbiter.lock"

    if action == LOCK_ACQUIRE:
        try:
            # Open the lockfile in exclusive mode
            # If the file exists and is locked, this will raise an IOError
            # If the file does not exist, it will be created.
            lockfile_path.touch(exist_ok=False)
            _lock_file = open(lockfile_path, "r+")
            fcntl.flock(_lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Store the file object to keep the lock active
            # This is a simple way to keep it in memory for the duration of the process.
            # In a more complex scenario, this might be managed by a global object.
            setattr(manage_lockfile, '_lock_file', _lock_file)
            print(f"✅ Lock acquired: {lockfile_path}")
        except FileExistsError:
            print(f"❌ Another Orbiter instance is already running. Lockfile exists: {lockfile_path}")
            raise RuntimeError("Another Orbiter instance is already running.")
        except IOError as e:
            print(f"❌ Failed to acquire lock: {e}. Another Orbiter instance might be running or lock is corrupted.")
            raise RuntimeError("Failed to acquire application lock.")
    elif action == LOCK_RELEASE:
        if hasattr(manage_lockfile, '_lock_file'):
            fcntl.flock(getattr(manage_lockfile, '_lock_file'), fcntl.LOCK_UN)
            getattr(manage_lockfile, '_lock_file').close()
            delattr(manage_lockfile, '_lock_file')
        
        if lockfile_path.exists():
            os.remove(lockfile_path)
            print(f"🗑️ Lock released and file removed: {lockfile_path}")
        else:
            print(f"⚠️ Lockfile not found during release, perhaps already removed: {lockfile_path}")
