import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api_helper import ShoonyaApiPy
import yaml
import logging

class BrokerClient:
    def __init__(self, simulate: bool = False):
        self.simulate = simulate
        self.api = ShoonyaApiPy()
        self.socket_opened = False
        self.SYMBOLDICT = {}
        
        # Load YOUR credentials (same as test_websocket_feed.py)
        with open('../cred.yml') as f:
            cred = yaml.load(f, Loader=yaml.FullLoader)
            self.cred = cred
            
        logging.basicConfig(level=logging.DEBUG)
        
    def login(self):
        ret = self.api.login(
            userid=self.cred['user'],
            password=self.cred['pwd'], 
            twoFA=self.cred['factor2'],
            vendor_code=self.cred['vc'],
            api_secret=self.cred['apikey'],
            imei=self.cred['imei']
        )
        return ret
    
    def start_feed(self):
        def event_handler_quote_update(message):
            key = message['e'] + '|' + message['tk']
            self.SYMBOLDICT[key] = message
            print(f"🔥 LIVE: {message['ts']} LTP: {message['lp']}")
        
        def open_callback():
            self.socket_opened = True
            print('🚀 ORBITER LIVE!')
            self.api.subscribe(['NSE|2885', 'NSE|11630'], feed_type='d')
        
        self.api.start_websocket(
            subscribe_callback=event_handler_quote_update,
            socket_open_callback=open_callback
        )
    
    def get_reliance_ltp(self):
        reliance = self.SYMBOLDICT.get('NSE|2885', {})
        return reliance.get('lp', 0)
    
    def close(self):
        self.api.close_websocket()
