import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api_helper import ShoonyaApiPy
import logging
import yaml

#enable dbug to see request and responses
logging.basicConfig(level=logging.DEBUG)

#start of our program
api = ShoonyaApiPy(broker="flattrade")
api2 = ShoonyaApiPy(broker="flattrade")

#credentials - use Flattrade credentials
with open('cred.yml') as f:
    cred = yaml.safe_load(f)
    print(cred)

ret = api.login(userid = cred['user'], password = cred['pwd'], 
                 twoFA=cred.get('factor2') or '', 
                 vendor_code=cred.get('vc') or '', 
                 api_secret=cred['apikey'], 
                 imei=cred.get('imei') or '')

if not ret or ret.get('stat') != 'Ok':
    print(f"❌ Login failed: {ret}")
    sys.exit(1)

usersession = ret['susertoken']

ret = api2.set_session(userid= cred['user'], password = cred['pwd'], usertoken= usersession)

pos = api2.get_positions()
print(pos)
pos = api.get_positions()

print(pos)