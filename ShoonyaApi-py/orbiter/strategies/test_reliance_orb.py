#!/usr/bin/env python3
import sys, os
import yaml

with open('cred.yml') as f:
    cred = yaml.load(f, Loader=yaml.FullLoader)
    print(cred)

# FIXED PATH - Go up 2 levels from strategies/
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, base_dir)

from api_helper import ShoonyaApiPy 

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir)
import config
from filters.entry.f1_orb import calculate_orb_range
from datetime import datetime

# Your creds + login
api = ShoonyaApiPy()
ret = api.login(userid = cred['user'], password = cred['pwd'], twoFA=cred['factor2'], vendor_code=cred['vc'], api_secret=cred['apikey'], imei=cred['imei'])
# api.login(cred['user'], cred['pwd'], cred['factor2'])

print("🧪 TESTING RELIANCE (2885) ORB")
token = '2885'  # or 'NSE|2885'

# Test 1: Fixed ORB (expect "no data")
print("1. 9:15-9:30 (old data)")
# upper1, lower1 = calculate_orb_range(api, token, "09:15", "09:30")
upper1, lower1 = calculate_orb_range(api, token,datetime.today() , datetime.today())
print(f"   → High={upper1}, Low={lower1}")

# Test 2: LIVE range (should work)
print("2. Last 15min (LIVE)")
upper2, lower2 = calculate_orb_range(api, token, datetime.today(), datetime.today())
print(f"   → High={upper2}, Low={lower2}")

# api.close_api()
