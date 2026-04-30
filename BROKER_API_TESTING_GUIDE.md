# Broker API Testing Guide

Complete reference for all broker API test files, how to use them, expected outputs, and troubleshooting for Kurma and Varaha trading systems.

---

## Quick Start

### For Kurma Users
```bash
# 1. Verify broker authentication
cd /home/trading_ceo/python-trader/ShoonyaApi-py/tests
python3 -m pytest test_broker_config.py -v

# 2. Test token generation (Shoonya only)
cd /home/trading_ceo/python-trader/Shoonya_oAuthAPI-py
python3 GetAuthcode.py

# 3. Test OHLC data retrieval
python3 << 'EOF'
from api_helper import NorenApiPy
import yaml

with open('cred.yml') as f:
    cred = yaml.safe_load(f)

api = NorenApiPy()
if api.set_session(userid=cred['UID'], accesstoken=cred['Access_token']):
    # Test CRUDEOILM token mapping
    ohlc = api.get_time_price_series(
        exchange='MCX',
        token='488291',  # CRUDEOILM
        starttime=1719792600,
        endtime=1719796200,
        interval=5
    )
    print(f"OHLC Data: {ohlc}")
else:
    print("Session failed")
EOF
```

### For Varaha Users
```bash
# 1. Test broker configuration
cd /home/trading_ceo/python-trader/ShoonyaApi-py/tests
python3 -m pytest test_broker_config.py::TestBrokerConfig -v

# 2. Test margin API
python3 << 'EOF'
from api_helper import NorenApiPy
import json

with open('FlattradeApi-py/tokens.json') as f:
    tokens = json.load(f)

api = NorenApiPy()
if api.set_session(userid=tokens['client'], accesstoken=tokens['token']):
    margin = api.get_limits()
    print(f"Available Margin: ₹{margin.get('cash')}")
else:
    print("Session failed")
EOF
```

---

## Test File Index

### 1. Broker Configuration Tests

#### Location
```
ShoonyaApi-py/tests/test_broker_config.py
```

#### What It Tests
- Broker configuration loading (Shoonya, Flattrade, Simulation)
- API endpoint correctness
- Broker initialization
- Simulation mode operation
- Credential file parsing

#### Test Cases
| Test | Purpose | Expected Result |
|------|---------|-----------------|
| `test_get_shoonya_config` | Verify Shoonya endpoints | Returns config with api.shoonya.com |
| `test_get_flattrade_config` | Verify Flattrade endpoints | Returns config with pi.flattrade.in |
| `test_get_simulation_config` | Verify simulation mode | Returns config with null endpoints |
| `test_broker_case_insensitive` | Case handling | All variations return same config |
| `test_simulation_get_funds` | Simulated margin | Returns ₹100,000 test funds |
| `test_simulation_get_positions` | Simulated positions | Returns empty list |
| `test_simulation_get_order_history` | Simulated orders | Returns empty list |

#### How to Run
```bash
cd /home/trading_ceo/python-trader/ShoonyaApi-py/tests
python3 -m pytest test_broker_config.py -v              # All tests
python3 -m pytest test_broker_config.py::TestBrokerConfig -v  # Broker config only
python3 -m pytest test_broker_config.py::TestSimulationMode -v # Simulation only
```

#### Expected Output
```
test_broker_config.py::TestBrokerConfig::test_get_shoonya_config PASSED
test_broker_config.py::TestBrokerConfig::test_get_flattrade_config PASSED
test_broker_config.py::TestBrokerConfig::test_get_simulation_config PASSED
test_broker_config.py::TestBrokerConfig::test_default_broker PASSED
test_broker_config.py::TestBrokerConfig::test_invalid_broker_raises_error PASSED
test_broker_config.py::TestBrokerConfig::test_broker_case_insensitive PASSED
test_broker_config.py::TestSimulationMode::test_simulation_mode_detection PASSED
test_broker_config.py::TestSimulationMode::test_shoonya_not_simulation PASSED
test_broker_config.py::TestSimulationMode::test_flattrade_not_simulation PASSED
test_broker_config.py::TestBrokerEndpoints::test_all_brokers_have_required_fields PASSED

======================== 10 passed in 0.23s ========================
```

#### Troubleshooting

**Issue: "No module named 'broker_config'"**
- Ensure you're in the correct directory: `cd ShoonyaApi-py/tests`
- Check that broker_config.py exists in parent directory

**Issue: "Test imports fail"**
- Verify all dependencies installed: `pip install pytest pyyaml`
- Check Python path includes parent directory

---

### 2. Shoonya OAuth Token Generation

#### Location
```
Shoonya_oAuthAPI-py/GetAuthcode.py
```

#### What It Does
Automates OAuth2 token generation without storing passwords in memory.

#### Prerequisites
```bash
# Install dependencies
pip install selenium pyotp pyyaml requests

# Ensure Chrome is installed
which google-chrome-stable  # Should output /usr/bin/google-chrome-stable
```

#### How to Run
```bash
cd /home/trading_ceo/python-trader/Shoonya_oAuthAPI-py
python3 GetAuthcode.py
```

#### Expected Output
```
[INFO] Trying Chrome binary: /usr/bin/google-chrome-stable
[SUCCESS] Chrome driver created using: /usr/bin/google-chrome-stable
Logging in to Shoonya (background)...
Credentials submitted. Capturing auth code...
Auth Code: a1b2c3d4-e5f6-7890-abcd-ef1234567890

✅ Auth code captured: a1b2c3d4-e5f6-7890-abcd-ef1234567890
🔐 Generating access token...
✅ Access token generated successfully!
   Access Token: 5f7987d9dca1d904bfb9ac1d329d102af8639e7a...
   User ID: FA333160
   Account ID: FA333160

✅ cred.yml updated with new access token!
```

#### What Gets Updated
After successful run, `cred.yml` is updated with:
```yaml
Access_token: <new-fresh-token>
Account_ID: FA333160
Secret_Code: iXR933DiPNljaFPegn5l3p9OcinEg6Ho0OOnFolxnn1niZkGggGc1i5q7dFqLopo
UID: FA333160
client_id: FA333160_U
oauth_url: https://api.shoonya.com/NorenWeb/authorize/oauth
```

#### Troubleshooting

**Issue: "DevToolsActivePort file doesn't exist"**
```bash
# Kill hanging Chrome processes
pkill -f chrome
pkill -f chromium
sleep 2

# Try again
python3 GetAuthcode.py
```

**Issue: "No Chrome binary available"**
```bash
# Install Google Chrome
sudo apt-get update
sudo apt-get install google-chrome-stable

# Verify installation
which google-chrome-stable
```

**Issue: "NameError: name 'yaml' is not defined"**
```bash
pip install pyyaml
```

**Issue: "Failed to capture auth code after 60 seconds"**
- Check internet connection is stable
- Verify USERNAME/PASSWORD/TOTP_SECRET in GetAuthcode.py are correct
- Check if Shoonya login page has changed
- Try running with timeout: `timeout 120 python3 GetAuthcode.py`

---

### 3. Shoonya OAuth Test Page

#### Location
```
Shoonya_oAuthAPI-py-main/test_shoonya.py
```

#### What It Does
Lightweight test that:
- Loads Shoonya login page in headless Chrome
- Displays form fields available
- Shows all buttons on page
- Takes screenshot for debugging

#### How to Run
```bash
cd /home/trading_ceo/python-trader/Shoonya_oAuthAPI-py-main
python3 test_shoonya.py
```

#### Expected Output
```
Login URL: https://trade.shoonya.com/OAuthlogin/investor-entry-level/login?api_key=FA333160_U&route_to=FA333160
Loading Shoonya login page...
Current URL: https://trade.shoonya.com/OAuthlogin/investor-entry-level/login?api_key=FA333160_U&route_to=FA333160
Page title: Shoonya | Login

=== Input Fields ===
  [0] type=text, placeholder=User ID, visible=True
  [1] type=password, placeholder=Password, visible=True
  [2] type=text, placeholder=OTP/TOTP, visible=True
  [3] type=hidden, placeholder=None, visible=False

=== Buttons ===
  [0] text='LOGIN', visible=True

Screenshot: /tmp/shoonya_login.png
Done
```

#### Use Cases
- Verify Shoonya login page is accessible
- Check if form fields have changed (maintenance indicator)
- Validate CSS selectors for automation scripts
- Debug GetAuthcode.py failures (screenshot in /tmp/shoonya_login.png)

---

### 4. Flattrade Order Test

#### Location
```
flattrade_test_order.py
```

#### What It Tests
- Flattrade OAuth token authentication
- Order placement API (AMO, limit orders)
- Session validation

#### Prerequisites
1. Flattrade token must be in `FlattradeApi-py/tokens.json`:
```json
{
  "client": "FT055702",
  "token": "your_oauth_token_here"
}
```

2. Verify endpoint connectivity:
```bash
curl -s https://pi.flattrade.in/
```

#### How to Run
```bash
cd /home/trading_ceo/python-trader
python3 flattrade_test_order.py
```

#### Expected Output (Success)
```
Using token: eyJhbGciOiJIUzI1NiIs...
set_session result: True
Order Result: {'stat': 'Ok', 'norenordno': 'SID123456789', 'exch': 'NSE', 'tradingsymbol': 'NIFTYBEES-EQ', 'quantity': '1', 'orderstatus': 'PENDING'}
```

#### Expected Output (Failure - MCX Not Enabled)
```
Using token: eyJhbGciOiJIUzI1NiIs...
set_session result: True
Order Result: {'stat': 'Not_Ok', 'emsg': 'MCX segment not enabled for this account'}
```

#### Expected Output (Failure - IP Not Whitelisted)
```
Using token: eyJhbGciOiJIUzI1NiIs...
set_session result: True
Order Result: {'stat': 'Not_Ok', 'emsg': 'Invalid IP address'}
```

#### Troubleshooting

**Issue: "tokens.json not found"**
```bash
# Generate token from Flattrade web portal
# Place in FlattradeApi-py/tokens.json:
echo '{"client":"FT055702","token":"your_token"}' > FlattradeApi-py/tokens.json
```

**Issue: "MCX segment not enabled for this account"**
- Log into Flattrade web portal
- Go to Settings → Segments
- Enable MCX trading
- Wait for margin availability

**Issue: "Invalid IP address"**
- Get your current IP: `curl https://whatismyip.com`
- Log into Flattrade admin portal
- Add your IP to API whitelist

---

### 5. Orbiter Broker Tests

#### Location
```
orbiter/tests/brokers/
```

#### Test Files
| File | Purpose | Brokers |
|------|---------|---------|
| `test_broker_config.py` | Configuration validation | All |
| `test_connection_and_debrief.py` | Login/logout flow | All |
| `test_broker_facade.py` | API wrapper methods | All |
| `test_tpSeries.py` | Historical OHLC data | Shoonya BFO |
| `test_margin.py` | Margin API | All |
| `test_resolver.py` | Symbol token mapping | All |
| `test_shoonya_api.py` | Shoonya specific | Shoonya |

#### Running Orbiter Tests
```bash
cd /home/trading_ceo/python-trader

# Run all broker tests
python3 -m pytest orbiter/tests/brokers/ -v

# Run specific test
python3 -m pytest orbiter/tests/brokers/test_margin.py -v

# Run with output
python3 -m pytest orbiter/tests/brokers/test_tpSeries.py -v -s

# Run single test function
python3 -m pytest orbiter/tests/brokers/test_tpSeries.py::test_bfo_tpseries_sensex_future -v
```

#### Key Test: TPSeries (OHLC Data)

**File:** `orbiter/tests/brokers/test_tpSeries.py`

**Tests:**
- `test_bfo_tpseries_sensex_future`: Sensex future 1-min candles
- `test_bfo_tpseries_sensex_option`: Sensex option 1-min candles
- `test_mcx_tpseries_crude`: MCX CRUDE oil 1-min candles
- `test_nfo_tpseries_nifty`: NFO Nifty future 1-min candles

**Expected Output:**
```
test_bfo_tpseries_sensex_future PASSED
[BFO Future] Token: 825565 (SENSEX26MARFUT)
  Request: 2026-04-30 10:00:00 to 2026-04-30 11:00:00
  Response type: <class 'list'>
  Candles: [{'time': 1719792600, 'open': 85245.5, 'high': 85250.0, 'low': 85240.0, 'close': 85248.0, 'volume': 1250}, ...]

test_bfo_tpseries_sensex_option PASSED
[BFO Option] Token: 863172 (SENSEX26MAY8500PE)
  Candles: 12 records

test_mcx_tpseries_crude PASSED
[MCX Crude] Token: 488291 (CRUDEOILM)
  Candles: 48 records (1-min)

test_nfo_tpseries_nifty PASSED
[NFO Nifty] Token: 99926009 (NIFTY26APR25000CE)
  Candles: 60 records (1-min)
```

#### Key Test: Margin API

**File:** `orbiter/tests/brokers/test_margin.py`

**Tests:**
- `test_shoonya_margin_available`: Available margin from Shoonya
- `test_flattrade_margin_available`: Available margin from Flattrade
- `test_margin_sufficient_for_position`: Position sizing validation

**Expected Output:**
```
test_shoonya_margin_available PASSED
  Shoonya Margin: ₹92,271.27 available

test_flattrade_margin_available PASSED
  Flattrade Margin: ₹0.00 available (MCX not enabled)

test_margin_sufficient_for_position PASSED
  Can place 4 CRUDEOILM contracts with available margin
```

---

## Integration with Kurma

### Token Mapping for MCX

Kurma uses numeric token IDs for MCX symbols. These are mapped in `kurma_auth.py`:

```python
def _get_token_for_instrument(self, instrument):
    token_map = {
        'CRUDEOILM': '488291',   # CRUDEOILM 18-MAY-2026
        'GOLDM': '487819',       # GOLDM 05-MAY-2026
        'SILVERM': '457533',     # SILVERM 30-APR-2026
        'NATGASM': '488506',     # NATGASMINI 26-MAY-2026
    }
    return token_map.get(instrument)
```

**How to Update Token Mapping:**

1. Run MCX test to get current tokens:
```bash
python3 orbiter/tests/brokers/test_tpSeries.py
```

2. Extract token from response and update `kurma_auth.py`

3. Verify with OHLC test:
```bash
cd kurma
python3 << 'EOF'
from kurma_auth import FlattradeAuth  # or ShoonyaAuth
auth = ShoonyaAuth()
token = auth._get_token_for_instrument('CRUDEOILM')
print(f"Token for CRUDEOILM: {token}")
EOF
```

---

## Integration with Varaha

### Broker Configuration in Varaha

Varaha uses the same broker config system as Kurma:

```python
from api_helper import NorenApiPy, ShoonyaApiPy, FlattradeApiPy

# Auto-select broker from cred file
api = NorenApiPy(cred_file='cred.yml')  # Defaults to Shoonya

# Or explicit selection
api = ShoonyaApiPy(broker='shoonya')
api = FlattradeApiPy()
```

### Testing Varaha Data Feed

```bash
cd /home/trading_ceo/python-trader

# Test Nifty data (NFO)
python3 << 'EOF'
from api_helper import NorenApiPy
import yaml

with open('ShoonyaApi-py/cred.yml') as f:
    cred = yaml.safe_load(f)

api = NorenApiPy()
if api.set_session(userid=cred['UID'], accesstoken=cred['Access_token']):
    # Nifty token: 99926009
    ohlc = api.get_time_price_series(
        exchange='NFO',
        token='99926009',
        starttime=1719792600,
        endtime=1719796200,
        interval=5
    )
    print(f"Nifty OHLC: {len(ohlc)} candles")
else:
    print("Session failed")
EOF

# Test BFO data (Sensex)
python3 << 'EOF'
from api_helper import NorenApiPy
import yaml

with open('ShoonyaApi-py/cred.yml') as f:
    cred = yaml.safe_load(f)

api = NorenApiPy()
if api.set_session(userid=cred['UID'], accesstoken=cred['Access_token']):
    # SENSEX token: 825565
    ohlc = api.get_time_price_series(
        exchange='BFO',
        token='825565',
        starttime=1719792600,
        endtime=1719796200,
        interval=5
    )
    print(f"SENSEX OHLC: {len(ohlc)} candles")
else:
    print("Session failed")
EOF
```

---

## Debugging Checklist

### When Tests Fail

- [ ] **Verify credentials:**
  ```bash
  ls -la Shoonya_oAuthAPI-py/cred.yml
  cat Shoonya_oAuthAPI-py/cred.yml
  ```

- [ ] **Check broker connectivity:**
  ```bash
  curl -I https://api.shoonya.com/
  curl -I https://pi.flattrade.in/
  ```

- [ ] **Test authentication:**
  ```bash
  python3 << 'EOF'
  from api_helper import NorenApiPy
  import yaml
  with open('Shoonya_oAuthAPI-py/cred.yml') as f:
      cred = yaml.safe_load(f)
  api = NorenApiPy()
  ret = api.set_session(userid=cred['UID'], accesstoken=cred['Access_token'])
  print(f"Session: {'OK' if ret else 'FAILED'}")
  EOF
  ```

- [ ] **Check token freshness:**
  - Token generation date in `cred.yml`
  - If > 30 days old, regenerate: `python3 Shoonya_oAuthAPI-py/GetAuthcode.py`

- [ ] **Verify test dependencies:**
  ```bash
  pip install pytest pyyaml selenium pyotp requests
  ```

- [ ] **Run with verbose output:**
  ```bash
  python3 -m pytest <test_file> -vv -s
  ```

---

## Common Issues & Solutions

### Issue: "Session Expired: Invalid Session Key"
**Cause:** OAuth token expired (Shoonya tokens: 30-60 days)
**Solution:**
```bash
cd Shoonya_oAuthAPI-py
python3 GetAuthcode.py
```

### Issue: "Connection refused" to Shoonya/Flattrade
**Cause:** Broker API unreachable
**Solution:**
```bash
# Test connectivity
curl -I https://api.shoonya.com/
curl -I https://pi.flattrade.in/

# Check firewall/proxy
ping -c 1 api.shoonya.com
```

### Issue: "MCX segment not enabled"
**Cause:** Account not configured for MCX trading
**Solution:**
- Log into broker web portal
- Go to Settings → Segments
- Enable MCX
- Wait for margin availability

### Issue: "Invalid IP address"
**Cause:** API key not whitelisted for your IP
**Solution:**
```bash
# Get your IP
curl https://whatismyip.com

# Whitelist in broker admin portal
# Add IP to API settings
```

### Issue: Chrome won't start in GetAuthcode.py
**Cause:** Chromium sandbox issues
**Solution:**
```bash
# Kill hanging processes
pkill -f chrome; pkill -f chromium

# Clean cache
rm -rf /tmp/chromium-data

# Try again
python3 GetAuthcode.py
```

---

## References

### Documentation Files
- `TOKEN_GENERATION_GUIDE.md` - OAuth token automation details
- `CREDENTIALS_README.md` - Credential file field reference
- `BROKER_AUTHENTICATION_GUIDE.md` - Broker setup and troubleshooting
- `kurma/README.md` - Kurma quick start
- `kurma/BROKER_AUTHENTICATION_GUIDE.md` - Kurma-specific broker setup

### Key Broker API Methods
| Method | Purpose | Returns |
|--------|---------|---------|
| `set_session(userid, accesstoken)` | Authenticate | True/False |
| `get_limits()` | Fetch margin | Dict with cash, collateral, etc. |
| `get_time_price_series(exchange, token, starttime, endtime, interval)` | OHLC data | List of candles |
| `place_order(...)` | Submit order | Dict with order status |
| `get_order_list()` | Fetch orders | List of orders |
| `get_positions()` | Fetch positions | List of positions |

### API Documentation Links
- Shoonya: https://shoonya.finvasia.com/api/documentation
- Flattrade: https://www.flattrade.in/api

---

**Last Updated:** 2026-04-30  
**Status:** ✅ Complete with all test files documented  
**Maintainer:** Kurma/Varaha Development Team
