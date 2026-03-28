#!/usr/bin/env python3
"""
Update test files to use shared api fixture from conftest.py
Removes individual login code and adds api fixture parameter.
"""
import os
import re
import glob

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

# Patterns to remove
patterns_to_remove = [
    # Remove api = ShoonyaApiPy()
    r"^api = ShoonyaApiPy\(\)\n",
    # Remove login() call with all parameters
    r"^ret = api\.login\(.*?\)\n",
    # Remove commented login
    r"^#ret = api\.login\(.*?\)\n",
]

def update_test_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    original = content
    
    # Remove api = ShoonyaApiPy()
    content = re.sub(r'^api = ShoonyaApiPy\(\)\n', '', content, flags=re.MULTILINE)
    
    # Remove ret = api.login(...) 
    content = re.sub(r'^ret = api\.login\(.*?\)\n', '', content, flags=re.DOTALL)
    
    # Remove commented #ret = api.login(...)
    content = re.sub(r'^#ret = api\.login\(.*?\)\n', '', content, flags=re.DOTALL)
    
    # Remove credential loading that's no longer needed
    content = re.sub(r"^#credentials.*? cred\['pwd'\].*?\n", '', content, flags=re.DOTALL)
    
    # Add api fixture parameter to test functions
    # Match: def test_xxx( or def test_xxx(api,
    content = re.sub(
        r'(def test_[a-zA-Z0-9_]+\()(.*?)(\):)',
        lambda m: m.group(1) + 'api, ' + m.group(2) + m.group(3) if 'api' not in m.group(2) else m.group(0),
        content
    )
    
    # Remove duplicate "api," if already present
    content = re.sub(r'def test_[a-zA-Z0-9_]+\(api,\s*api,', 'def test_', content)
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✅ Updated: {os.path.basename(filepath)}")
    else:
        print(f"⏭️  Skipped: {os.path.basename(filepath)} (no changes)")

def main():
    # Get all test_*.py files
    test_files = glob.glob(os.path.join(TESTS_DIR, 'test_*.py'))
    
    # Exclude conftest.py itself
    test_files = [f for f in test_files if not f.endswith('conftest.py')]
    
    print(f"Updating {len(test_files)} test files...\n")
    
    for filepath in test_files:
        update_test_file(filepath)
    
    print("\n✅ Done! Run tests with: pytest tests/ -v")

if __name__ == '__main__':
    main()
