# orbiter/utils/version.py

import os
import subprocess
from datetime import datetime

def load_version(project_root: str) -> str:
    """
    Loads the application version by combining data from version.txt and git.
    This centralized utility handles all version-string construction.
    """
    version_file = os.path.join(project_root, 'version.txt')
    
    # 1. Base Version from File
    try:
        if os.path.exists(version_file):
            with open(version_file, 'r') as f:
                base_v = f.read().strip()
        else: 
            base_v = "0.0.0"
    except Exception: 
        base_v = "0.0.0"

    # 2. Dynamic Metadata (Date + Git Hash)
    try:
        # Get short git hash
        git_hash = subprocess.check_output(
            ['git', 'rev-parse', '--short=7', 'HEAD'], 
            stderr=subprocess.DEVNULL, 
            cwd=project_root
        ).decode('ascii').strip()
        
        date_str = datetime.now().strftime('%Y%m%d')
        return f"{base_v}-{date_str}-{git_hash}"
    except Exception:
        # Fallback to base version if git is unavailable
        return base_v
