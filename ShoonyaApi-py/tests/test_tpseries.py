import os, sys
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, base_dir) 
from api_helper import ShoonyaApiPy
import logging
import yaml
import datetime
import timeit
import pytz

#supress debug messages for prod/tests
logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(level=logging.INFO)


#start of our program
api = ShoonyaApiPy()


#use following if yaml isnt used
#user    = <uid>
#pwd     = <password>
#factor2 = <2nd factor>
#vc      = <vendor code>
#apikey  = <secret key>
#imei    = <imei>

#ret = api.login(userid = user, password = pwd, twoFA=factor2, vendor_code=vc, api_secret=apikey, imei=imei)

#yaml for parameters
cred_path = os.path.join(base_dir, 'cred.yml')
with open(cred_path) as f:
    cred = yaml.load(f, Loader=yaml.FullLoader)

ret = api.login(userid = cred['user'], password = cred['pwd'], twoFA=cred['factor2'], vendor_code=cred['vc'], api_secret=cred['apikey'], imei=cred['imei'])

if ret != None:
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.datetime.now(tz=ist)
    lastBusDay = now_ist - datetime.timedelta(days=1)
    while lastBusDay.weekday() >= 5:
        lastBusDay = lastBusDay - datetime.timedelta(days=1)

    start_dt = lastBusDay.replace(hour=9, minute=15, second=0, microsecond=0)
    end_dt = lastBusDay.replace(hour=15, minute=30, second=0, microsecond=0)

    starttime = timeit.default_timer()
    print("The start time is :",starttime)
    # get previous trading day's intraday data (IST)
    ret = api.get_time_price_series(
        exchange='NSE',
        token='2885',
        starttime=start_dt.timestamp(),
        endtime=end_dt.timestamp(),
        interval=240
    )


    #ret = api.get_time_price_series(exchange='NSE', token='2885', starttime=lastBusDay.timestamp())
    #ret = api.get_time_price_series(exchange='NSE', token='2885' , interval=5)

    

    if ret != None:
        print(ret)
        #for val in ret:
        #    print(val)

   # print("The time difference is :", timeit.default_timer() - starttime)