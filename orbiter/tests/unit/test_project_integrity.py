
import unittest
import os
import sys
import json

# Precise Path Resolution to get to project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from orbiter.utils.data_manager import DataManager

def validate_project_structure(project_root: str, manifest: dict = None) -> tuple[bool, str]:
    """
    INTERNAL TEST UTILITY: Ensures the project_root contains all 
    mandatory files defined in the manifest.
    """
    if not manifest:
        manifest = DataManager.load_manifest(project_root)
    
    # 1. Validate mandatory directories
    for key, rel_path in manifest.get('structure', {}).items():
        full_path = os.path.join(project_root, rel_path)
        if not os.path.exists(full_path):
            return False, f"Manifest directory '{key}' missing: {rel_path}"
            
    # 2. Validate mandatory files/dependencies
    for key, rel_path in manifest.get('mandatory_files', {}).items():
        full_path = os.path.join(project_root, rel_path)
        if not os.path.exists(full_path):
            return False, f"Manifest mandatory item '{key}' missing: {rel_path}"
            
    return True, ""

class TestProjectIntegrity(unittest.TestCase):
    """
    SMOKE TEST: Runs against the ACTUAL filesystem to ensure 
    the project is in a valid state for execution.
    """

    def test_mandatory_files_exist(self):
        """Verify that all mandatory pillars are present."""
        is_valid, error_msg = validate_project_structure(project_root)
        
        self.assertTrue(is_valid, f"❌ Project Integrity Failed: {error_msg}")
        print(f"✅ Project Integrity Verified at: {project_root}")

    def test_config_validity(self):
        """Verify that mandatory JSON configs are actually valid JSON."""
        manifest = DataManager.load_manifest(project_root)
        
        configs = list(manifest.get('mandatory_files', {}).values())
        configs.append('project.json')

        for rel_path in configs:
            full_path = os.path.join(project_root, rel_path)
            if not os.path.isfile(full_path): continue
            
            with self.subTest(config=rel_path):
                with open(full_path, 'r') as f:
                    try:
                        json.load(f)
                    except json.JSONDecodeError as e:
                        self.fail(f"Invalid JSON in {rel_path}: {e}")

if __name__ == '__main__':
    unittest.main()
