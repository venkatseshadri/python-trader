#!/usr/bin/env python3
"""
Debug Login Test - Shows ALL details sent to Shoonya API login
================================================================
Enhanced version with maximum debug output
"""
import yaml
import hashlib
import pyotp
import logging
import json
import requests
import time
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

# ============================================================
# MAXIMUM DEBUG LOGGING - Capture everything
# ============================================================

# Create detailed logger for HTTP requests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Enable urllib3 debug (shows HTTP headers, connectionpool)
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.DEBUG)
urllib3_logger.addHandler(logging.StreamHandler())

# Import the API
import sys
sys.path.insert(0, '/home/trading_ceo/python-trader/ShoonyaApi-py')
from api_helper import ShoonyaApiPy

def main():
    print("\n" + "=" * 80)
    print("🔍 SHOONYA API - MAXIMUM DEBUG LOGIN TEST")
    print("=" * 80 + "\n")
    
    # ============================================================
    # STEP 1: Load and display credentials
    # ============================================================
    print("📄 STEP 1: Loading credentials from cred.yml")
    print("-" * 60)
    
    cred_path = '/home/trading_ceo/python-trader/ShoonyaApi-py/cred.yml'
    with open(cred_path, 'r') as f:
        cred = yaml.safe_load(f)
    
    # Print raw credentials (masked)
    print(f"  📌 userid:     '{cred.get('user', 'NOT SET')}'")
    print(f"  📌 pwd:        '{cred.get('pwd', 'NOT SET')}'")
    print(f"  📌 apikey:     '{cred.get('apikey', 'NOT SET')}'")
    print(f"  📌 vc:         '{cred.get('vc', 'NOT SET')}'")
    print(f"  📌 totp_key:   '{cred.get('totp_key', 'NOT SET')}'")
    print(f"  📌 imei:       '{cred.get('imei', 'NOT SET')}'")
    print(f"  📌 broker:     '{cred.get('broker', 'NOT SET')}'")
    
    # ============================================================
    # STEP 2: Prepare each login parameter
    # ============================================================
    print("\n📋 STEP 2: Preparing login parameters")
    print("-" * 60)
    
    uid = cred.get('user', '')
    pwd_raw = cred.get('pwd', '')
    api_secret_raw = cred.get('apikey', '')
    vc = cred.get('vc', '')
    totp_key = cred.get('totp_key', '')
    imei = cred.get('imei', 'abc1234')
    
    # 2a. Password - SHA256 encoded (what the API expects)
    pwd_sha256 = hashlib.sha256(pwd_raw.encode('utf-8')).hexdigest()
    print(f"  🔑 password (raw):        '{pwd_raw}'")
    print(f"  🔑 password (SHA256):    '{pwd_sha256}'")
    
    # 2b. TOTP factor2
    if totp_key:
        totp = pyotp.TOTP(totp_key)
        factor2 = totp.now()
        print(f"  🔐 factor2 (TOTP now):   '{factor2}'")
        print(f"  🔐 totp_key (source):    '{totp_key}'")
    else:
        factor2 = ""
        print(f"  🔐 factor2:              'NOT SET'")
    
    # 2c. Vendor code
    print(f"  🏢 vendor_code (vc):     '{vc}'")
    
    # 2d. App Key - SHA256(userid + api_secret)
    # This is the critical one that the server validates!
    app_key_raw = f"{uid}|{api_secret_raw}"
    app_key_sha256 = hashlib.sha256(app_key_raw.encode('utf-8')).hexdigest()
    print(f"  🔗 app_key input:        '{app_key_raw}'")
    print(f"  🔗 app_key (SHA256):    '{app_key_sha256}'")
    print(f"  📊 app_key length:      {len(app_key_sha256)} chars")
    
    # 2e. IMEI
    print(f"  📱 imei:                 '{imei}'")
    
    # ============================================================
    # STEP 3: Show the FINAL JSON payload being sent
    # ============================================================
    print("\n📦 STEP 3: Final JSON payload (jData)")
    print("-" * 60)
    
    payload_dict = {
        "source": "API",
        "apkversion": "1.0.0",
        "uid": uid,
        "pwd": pwd_sha256,
        "factor2": factor2,
        "vc": vc,
        "appkey": app_key_sha256,
        "imei": imei
    }
    
    # Pretty print the JSON
    payload_json = json.dumps(payload_dict, indent=2)
    print(payload_json)
    
    # Also show URL-encoded format
    from urllib.parse import urlencode
    url_encoded = urlencode({"jData": json.dumps(payload_dict)})
    print(f"\n🔗 URL-encoded: {url_encoded[:80]}...")
    
    # ============================================================
    # STEP 4: Make the HTTP request manually (maximum control)
    # ============================================================
    print("\n🌐 STEP 4: Making HTTP request to Shoonya API")
    print("-" * 60)
    
    # API endpoint
    url = "https://api.shoonya.com/NorenWClientTP//QuickAuth"
    print(f"  📍 URL: {url}")
    print(f"  ⏰ Request time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Custom session with retries
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    # Prepare headers
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'User-Agent': 'ShoonyaApi-Py/1.0',
        'Accept-Encoding': 'gzip, deflate'
    }
    print(f"  📋 Headers: {headers}")
    
    # Send request
    print("\n  ⏳ Sending request...")
    start_time = time.time()
    
    try:
        response = session.post(
            url,
            data=url_encoded,
            headers=headers,
            timeout=30
        )
        elapsed = time.time() - start_time
        
        print(f"\n  ✅ Response received in {elapsed:.3f}s")
        print(f"  📊 Status Code: {response.status_code}")
        print(f"  📊 Response Headers: {dict(response.headers)}")
        
        # Parse response
        try:
            resp_json = response.json()
            print(f"\n  📥 Response Body (JSON):")
            print(json.dumps(resp_json, indent=4))
        except:
            print(f"\n  📥 Response Body (raw): {response.text}")
        
    except requests.exceptions.Timeout:
        print("  ❌ Request timed out!")
    except requests.exceptions.ConnectionError as e:
        print(f"  ❌ Connection error: {e}")
    except Exception as e:
        print(f"  ❌ Error: {type(e).__name__}: {e}")
    
    # ============================================================
    # STEP 5: Also try using the library (for comparison)
    # ============================================================
    print("\n" + "=" * 80)
    print("🔄 STEP 5: Now trying api.login() from library")
    print("=" * 80)
    
    api = ShoonyaApiPy()
    
    print("\nCalling api.login() with parameters:")
    print(f"  userid='{uid}'")
    print(f"  password='{pwd_raw}'")
    print(f"  twoFA='{factor2}'")
    print(f"  vendor_code='{vc}'")
    print(f"  api_secret='{api_secret_raw}'")  
    print(f"  imei='{imei}'")
    
    ret = api.login(
        userid=uid,
        password=pwd_raw,
        twoFA=factor2,
        vendor_code=vc,
        api_secret=api_secret_raw,
        imei=imei
    )
    
    print("\n" + "=" * 80)
    print("📊 FINAL RESULT")
    print("=" * 80)
    print(f"Return value: {ret}")
    
    if ret is None:
        print("\n❌ LOGIN FAILED - Returned None")
        print("   This means the API returned stat != 'Ok'")
    elif ret.get('stat') == 'Ok':
        print("\n✅ LOGIN SUCCESS!")
        print(f"   User token: {ret.get('susertoken', 'N/A')[:20]}...")
    else:
        print(f"\n❌ LOGIN FAILED: {ret}")
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    main()