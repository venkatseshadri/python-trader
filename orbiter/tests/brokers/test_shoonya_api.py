import pytest
import os
import yaml
import datetime
import pytz
import requests
import zipfile
from api_helper import ShoonyaApiPy

# Configuration for scrip masters
MASTERS = ['NSE_symbols.txt.zip', 'NFO_symbols.txt.zip', 'MCX_symbols.txt.zip']
ROOT_URL = 'https://api.shoonya.com/'

def get_credentials():
    # Look for credentials in multiple possible locations
    possible_paths = [
        '../ShoonyaApi-py/cred.yml',
        '../../ShoonyaApi-py/cred.yml',
        'python-trader/ShoonyaApi-py/cred.yml'
    ]
    for p in possible_paths:
        if os.path.exists(p):
            with open(p) as f:
                cred = yaml.load(f, Loader=yaml.FullLoader)
                # Simple check to see if it's not placeholders
                if cred.get('user') and 'your_' not in str(cred.get('user')):
                    return cred
    return None

CREDENTIALS = get_credentials()

@pytest.fixture(scope="module")
def api():
    if not CREDENTIALS:
        pytest.skip("No valid Shoonya credentials found in cred.yml")
    
    shoonya = ShoonyaApiPy()
    ret = shoonya.login(
        userid=CREDENTIALS['user'],
        password=CREDENTIALS['pwd'],
        twoFA=CREDENTIALS['factor2'],
        vendor_code=CREDENTIALS['vc'],
        api_secret=CREDENTIALS['apikey'],
        imei=CREDENTIALS['imei']
    )
    if not ret or ret.get('stat') != 'Ok':
        pytest.skip(f"Login failed: {ret.get('emsg') if ret else 'No response'}")
    
    yield shoonya
    shoonya.close_websocket()

@pytest.mark.parametrize("zip_file", MASTERS)
def test_scrip_master_download_urls(zip_file):
    """Validate that Shoonya scrip master download URLs are active and return valid ZIPs"""
    url = ROOT_URL + zip_file
    response = requests.get(url, allow_redirects=True, timeout=10)
    assert response.status_code == 200
    assert len(response.content) > 1000 # Should be at least 1KB
    
    # Verify it is a valid zip (optional check)
    with open(f"temp_{zip_file}", 'wb') as f:
        f.write(response.content)
    try:
        with zipfile.ZipFile(f"temp_{zip_file}") as z:
            assert len(z.namelist()) > 0
    finally:
        if os.path.exists(f"temp_{zip_file}"):
            os.remove(f"temp_{zip_file}")

def test_authentication_and_user_details(api):
    """Verify that we can retrieve user details after login"""
    details = api.get_user_details()
    assert details is not None
    assert details.get('stat') == 'Ok'
    assert 'actid' in details

def test_time_price_series_fetch(api):
    """Verify fetching of historical candle data for a standard token (NSE|26000 - NIFTY Index)"""
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(tz=ist)
    
    # Go back to last business day
    last_bus_day = now_ist - datetime.timedelta(days=1)
    while last_bus_day.weekday() >= 5: # Saturday/Sunday
        last_bus_day = last_bus_day - datetime.timedelta(days=1)

    start_dt = last_bus_day.replace(hour=10, minute=0, second=0, microsecond=0)
    end_dt = last_bus_day.replace(hour=11, minute=0, second=0, microsecond=0)

    # Note: 26000 is NIFTY Index
    ret = api.get_time_price_series(
        exchange='NSE',
        token='26000',
        starttime=start_dt.timestamp(),
        endtime=end_dt.timestamp(),
        interval=1
    )
    
    assert ret is not None
    assert isinstance(ret, list)
    assert len(ret) > 0
    assert 'into' in ret[0] # Open
    assert 'inth' in ret[0] # High
