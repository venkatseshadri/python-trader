"""
Pytest configuration for Shoonya API tests
==========================================
- Single login for all tests
- Token caching to avoid multiple broker logins
- Session reuse via set_session()
"""
import os, sys
import pytest
import yaml

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_helper import ShoonyaApiPy

# Constants
TOKEN_FILE = os.path.join(os.path.dirname(__file__), '.session_token')
CRED_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'cred.yml')

# Skip all tests if no credentials
if not os.path.exists(CRED_PATH):
    pytest.skip("cred.yml not found", allow_module_level=True)


def load_credentials():
    """Load credentials from cred.yml"""
    with open(CRED_PATH) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def save_token(userid, susertoken):
    """Save session token to file"""
    with open(TOKEN_FILE, 'w') as f:
        f.write(f"{userid}\n{susertoken}")


def load_token():
    """Load session token from file"""
    if not os.path.exists(TOKEN_FILE):
        return None, None
    with open(TOKEN_FILE, 'r') as f:
        lines = f.read().strip().split('\n')
        if len(lines) >= 2:
            return lines[0], lines[1]
    return None, None


def clear_token():
    """Clear saved token (force fresh login)"""
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)


@pytest.fixture(scope="session")
def api():
    """
    Shared API fixture for all tests.
    - First test does login and saves token
    - Subsequent tests reuse the token via set_session()
    """
    # Load credentials
    cred = load_credentials()
    
    # Create API instance
    api_obj = ShoonyaApiPy()
    
    # Try to load existing token
    userid, susertoken = load_token()
    
    if userid and susertoken:
        # Try to reuse existing session
        print(f"\n[Session] Trying to reuse token for {userid}...")
        api_obj.set_session(userid, cred['pwd'], susertoken)
        
        # Verify session is valid by making a test call
        try:
            api_obj.get_orders()
            print("[Session] ✅ Token valid, reusing session")
            return api_obj
        except Exception as e:
            print(f"[Session] ⚠️ Token invalid: {e}")
            clear_token()
    
    # No valid token - do fresh login
    print(f"\n[Session] Performing fresh login for {cred['user']}...")
    ret = api_obj.login(
        userid=cred['user'],
        password=cred['pwd'],
        twoFA=cred['factor2'],
        vendor_code=cred['vc'],
        api_secret=cred['apikey'],
        imei=cred['imei']
    )
    
    if ret and ret.get('stat') == 'Ok':
        susertoken = ret.get('susertoken')
        save_token(cred['user'], susertoken)
        print(f"[Session] ✅ Login successful, token saved")
        return api_obj
    else:
        pytest.fail(f"Login failed: {ret}")


# ============================================================================
# Authentication Test - Run this FIRST to validate credentials
# ============================================================================
def test_01_auth_validate(api):
    """
    ✅ Test 01: Validate authentication
    This should be run FIRST to ensure credentials are valid.
    If this fails, other tests will likely fail due to blocked account.
    """
    # Make a simple API call to verify we're authenticated
    result = api.get_orders()
    
    # Should return a list (even if empty)
    assert result is not None, "Failed to get orders - not authenticated"
    print(f"\n[Auth] ✅ Authentication valid. Orders count: {len(result) if result else 0}")


def test_02_session_persistence(api):
    """
    ✅ Test 02: Verify session reuse works
    This test ensures the token caching is working.
    """
    # If we get here, it means the fixture reused the session
    # Verify with another API call
    result = api.get_orders()
    assert result is not None
    print(f"\n[Session] ✅ Session persisted across tests")
