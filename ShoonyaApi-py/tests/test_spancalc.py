import json
import os
import sys
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_helper import ShoonyaApiPy
import logging
import yaml
from NorenRestApiPy.NorenApi import position

#enable dbug to see request and responses
logging.basicConfig(level=logging.DEBUG)

#start of our program
api = ShoonyaApiPy()

#inputs
base_dir = os.path.dirname(__file__)
input_path = os.path.join(base_dir, 'ntpc_credit_spread.json')
with open(input_path) as f:
    inputs = json.load(f)


def _load_symbol_map(path: str):
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path) as handle:
            data = json.load(handle)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            options = data.get("options")
            return options if isinstance(options, list) else []
        return []
    except Exception:
        return []


def _parse_symbol_expiry(raw: str):
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except Exception:
        return None


def _format_span_expiry(raw_date):
    return raw_date.strftime("%d-%b-%Y").upper()


def _parse_span_expiry(raw: str):
    try:
        return datetime.strptime(raw.strip(), "%d-%b-%Y").date()
    except Exception:
        return None


def _select_current_expiry(rows, today):
    expiries = []
    for row in rows:
        parsed = _parse_symbol_expiry(row.get("expiry", ""))
        if parsed:
            expiries.append(parsed)
    if not expiries:
        return None
    expiries = sorted(set(expiries))
    for exp in expiries:
        if exp >= today:
            return exp
    return expiries[-1]


def _nearest_strike(rows, expiry, option_type, target):
    strikes = []
    for row in rows:
        if row.get("option_type") != option_type:
            continue
        parsed = _parse_symbol_expiry(row.get("expiry", ""))
        if parsed != expiry:
            continue
        try:
            strikes.append(float(row.get("strike")))
        except Exception:
            continue
    if not strikes:
        return target
    strikes = sorted(set(strikes))
    try:
        target_val = float(target)
    except Exception:
        target_val = strikes[len(strikes) // 2]
    return min(strikes, key=lambda val: abs(val - target_val))


def _format_strike(raw):
    try:
        value = float(raw)
        if value.is_integer():
            return str(int(value))
        return str(value)
    except Exception:
        return str(raw).strip()

cred_path = os.path.join(base_dir, inputs.get('credentials_path', '../cred.yml'))
with open(cred_path) as f:
    cred = yaml.load(f, Loader=yaml.FullLoader)

ret = api.login(
    userid=cred['user'],
    password=cred['pwd'],
    twoFA=cred['factor2'],
    vendor_code=cred['vc'],
    api_secret=cred['apikey'],
    imei=cred['imei'],
)

if not ret or ret.get('stat') != 'Ok':
    err = ret.get('emsg') if isinstance(ret, dict) else 'Unknown login error'
    print(f"Login failed: {err}")
    sys.exit(1)

positionlist = []
use_symbol_map = inputs.get("use_symbol_map", True)
force_expiry = inputs.get("force_expiry")
symbol_map_path = inputs.get("symbol_map_path")
if not symbol_map_path:
    symbol_map_path = os.path.abspath(
        os.path.join(base_dir, "..", "..", "orbiter", "data", "nfo_symbol_map.json")
    )
elif not os.path.isabs(symbol_map_path):
    symbol_map_path = os.path.abspath(os.path.join(base_dir, symbol_map_path))
symbol_map = _load_symbol_map(symbol_map_path) if use_symbol_map else []
today = datetime.now().date()

for leg in inputs.get('positions', []):
    pos = position()
    pos.prd = leg['prd']
    pos.exch = leg['exch']
    pos.instname = leg['instname']
    pos.symname = leg['symname']
    pos.optt = leg['optt']

    exd = leg.get("exd")
    strprc = leg.get("strprc")
    if force_expiry:
        exd = force_expiry.strip().upper()
    if symbol_map:
        rows = [
            row
            for row in symbol_map
            if row.get("symbol") == pos.symname and row.get("instrument") == pos.instname
        ]
        expiry = None
        if force_expiry:
            forced = _parse_span_expiry(force_expiry)
            if forced:
                expiry = forced
        if not expiry:
            expiry = _select_current_expiry(rows, today)
        if expiry:
            exd = _format_span_expiry(expiry)
            strprc = _nearest_strike(rows, expiry, pos.optt, strprc)

    pos.exd = exd
    pos.strprc = _format_strike(strprc)
    pos.buyqty = int(leg['buyqty'])
    pos.sellqty = int(leg['sellqty'])
    pos.netqty = int(leg['netqty'])
    positionlist.append(pos)

actid = inputs.get('actid') or cred['user']
senddata = {}
senddata['actid'] = actid
senddata['pos'] = positionlist
#payload = 'jData=' + json.dumps(senddata, default=lambda o: o.encode())
#print(payload)
ret = api.span_calculator(actid, positionlist)
print(ret)

span = float(ret.get('span', 0.0))
expo = float(ret.get('expo', 0.0))
total_margin = span + expo
haircut = float(inputs.get('haircut', 0.20))
pledged_required = total_margin / (1.0 - haircut) if total_margin else 0.0
print(f"span={span:.2f} expo={expo:.2f} total={total_margin:.2f}")
print(f"pledged_required_with_20pct_haircut={pledged_required:.2f}")