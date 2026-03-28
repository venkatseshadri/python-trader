#!/usr/bin/env python3
"""
test_single_user_session.py - With MAXIMUM TRACE/DEBUG logging
"""
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# TRACE/DEBUG: Enable all logging
# ============================================================
import logging
logging.basicConfig(level=logging.DEBUG)

# ============================================================
# TRACE: Import modules
# ============================================================
print("\n" + "="*70)
print("TRACE: Importing modules...")
print("="*70)

from api_helper import ShoonyaApiPy
import time
import yaml
import pyotp
import hashlib
import json

print("TRACE: All imports successful")

# ============================================================
# TRACE: Load credentials
# ============================================================
print("\n" + "="*70)
print("TRACE: Loading cred.yml...")
print("="*70)

with open('../cred.yml') as f:
    creds_user1 = yaml.load(f, Loader=yaml.FullLoader)

print("TRACE: cred.yml loaded successfully")
print("\nDEBUG: Raw credential values:")
for k, v in creds_user1.items():
    if k == 'pwd':
        print(f"  DEBUG: {k} = '{'*'*len(v)}' (masked)")
    elif k == 'apikey':
        print(f"  DEBUG: {k} = '{v}'")
    else:
        print(f"  DEBUG: {k} = '{v}'")

# ============================================================
# TRACE: Generate TOTP
# ============================================================
print("\n" + "="*70)
print("TRACE: Generating TOTP from totp_key...")
print("="*70)

print(f"DEBUG: totp_key = '{creds_user1['totp_key'].strip()}'")
totp = pyotp.TOTP(creds_user1['totp_key'].strip())
twoFA = totp.now()
print(f"TRACE: TOTP generated = '{twoFA}'")

# ============================================================
# TRACE: Create API instance
# ============================================================
print("\n" + "="*70)
print("TRACE: Creating ShoonyaApiPy instance...")
print("="*70)

import logging

# 1. Setup a basic format so you can see timestamps and levels
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)

# 2. Specifically set the NorenApi logger to DEBUG to see the JSON payloads
logging.getLogger('NorenRestApiPy.NorenApi').setLevel(logging.DEBUG)

# 3. (Optional) Silence the noisy connection pool logs if you only want the API data
logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)

user1 = ShoonyaApiPy()
print("TRACE: ShoonyaApiPy instance created")

# ============================================================
# TRACE: Prepare login parameters (show EVERYTHING)
# ============================================================
print("\n" + "="*70)
print("TRACE: Preparing login parameters...")
print("="*70)

uid = creds_user1['user']
pwd_raw = creds_user1['pwd']
api_secret = creds_user1['apikey']
vc = creds_user1['vc']
imei = creds_user1['imei']

print(f"DEBUG: uid (user)     = '{uid}'")
print(f"DEBUG: pwd_raw        = '{pwd_raw}'")
print(f"DEBUG: api_secret     = '{api_secret}'")
print(f"DEBUG: vc             = '{vc}'")
print(f"DEBUG: imei           = '{imei}'")
print(f"DEBUG: twoFA (TOTP)   = '{twoFA}'")

# Show SHA256 conversions
#pwd_sha256 = hashlib.sha256(pwd_raw.encode('utf-8')).hexdigest()
#app_key = hashlib.sha256(f"{uid}|{api_secret}".encode('utf-8')).hexdigest()

#print("\nDEBUG: SHA256 conversions:")
#print(f"  DEBUG: pwd (SHA256)    = '{pwd_sha256}'")
#print(f"  DEBUG: app_key (SHA256 of '{uid}|{api_secret}') = '{app_key}'")

# ============================================================
# TRACE: Build final payload (exact form sent to API)
# ============================================================
print("\n" + "="*70)
print("TRACE: Building final jData payload...")
print("="*70)

payload = {
    "source": "API",
    "apkversion": "1.0.0",
    "uid": uid,
    "pwd": pwd_raw,
    "factor2": twoFA,
    "vc": vc,
    "api_secret": api_secret,
    "imei": imei
}

print("DEBUG: Final jData payload:")
print(json.dumps(payload, indent=2))

# ============================================================
# TRACE: Call login() - this is where it connects
# ============================================================
print("\n" + "="*70)
print("TRACE: >>> CALLING user1.login() <<<")
print("="*70)
print("DEBUG: Calling with parameters:")
print(f"  user1.login(")
print(f"      userid='{uid}',")
print(f"      password='{pwd_raw}',")
print(f"      twoFA='{twoFA}',")
print(f"      vendor_code='{vc}',")
print(f"      api_secret='{api_secret}',")
print(f"      imei='{imei}'")
print(f"  )")

ret = user1.login(
    userid=uid,
    password=pwd_raw,
    twoFA=twoFA,
    vendor_code=vc,
    api_secret=api_secret,
    imei=imei
)

print("TRACE: login() returned")

# ============================================================
# TRACE: Process response
# ============================================================
print("\n" + "="*70)
print("TRACE: Processing login response...")
print("="*70)

print(f"DEBUG: ret = {ret}")
print(f"DEBUG: type(ret) = {type(ret)}")

if not ret:
    print("\n" + "="*70)
    print("TRACE: ret is None/False - LOGIN FAILED")
    print("="*70)
    print("Login failed! Cannot start websocket.")
    sys.exit(1)

print("\n" + "="*70)
print("TRACE: Login SUCCESS - continuing...")
print("="*70)

# ============================================================
# TRACE: WebSocket setup
# ============================================================
print("\n" + "="*70)
print("TRACE: Setting up WebSocket callbacks...")
print("="*70)

def user1_socket_order_update(message):
    print(f"TRACE: OrderInfo Received for User1: {message}")

def user1_socket_quote_update(message):
    print(f"TRACE: Quote Received for User1: {message}")

def user1_socket_open():
    print("TRACE: WebSocket opened for User1 - subscribing to NSE|26000")
    user1.subscribe('NSE|26000')

print("TRACE: Callbacks defined")

# ============================================================
# TRACE: Start WebSocket
# ============================================================
print("\n" + "="*70)
print("TRACE: Starting WebSocket...")
print("="*70)

user1.start_websocket(
    order_update_callback=user1_socket_order_update,
    subscribe_callback=user1_socket_quote_update,
    socket_open_callback=user1_socket_open
)

print("TRACE: start_websocket() called")
time.sleep(2)

print("\n" + "="*70)
print("TRACE: All initialization complete!")
print("="*70)
print("Accounts initialized, quotes/order updates should come for user.")
print("="*70)

prompt1 = input('what shall we do? ').lower()
