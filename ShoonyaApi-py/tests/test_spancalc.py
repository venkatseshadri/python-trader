import json
import os
import sys
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
for leg in inputs.get('positions', []):
    pos = position()
    pos.prd = leg['prd']
    pos.exch = leg['exch']
    pos.instname = leg['instname']
    pos.symname = leg['symname']
    pos.exd = leg['exd']
    pos.optt = leg['optt']
    pos.strprc = leg['strprc']
    pos.buyqty = leg['buyqty']
    pos.sellqty = leg['sellqty']
    pos.netqty = leg['netqty']
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