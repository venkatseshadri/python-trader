"""
Shoonya/Flattrade API Helper with Multi-Broker Support
=====================================================
Supports: Shoonya, Flattrade, Simulation Mode
"""
from NorenRestApiPy.NorenApi import NorenApi
from threading import Timer
import pandas as pd
import time
import concurrent.futures
import os
import yaml
import random

# Import broker config
from broker_config import get_broker_config, is_simulation_mode

api = None


class Order:
    def __init__(self, buy_or_sell=None, product_type=None,
                 exchange=None, tradingsymbol=None,
                 price_type=None, quantity=None,
                 price=None, trigger_price=None, discloseqty=0,
                 retention="DAY", remarks="tag",
                 order_id=None):
        self.buy_or_sell = buy_or_sell
        self.product_type = product_type
        self.exchange = exchange
        self.tradingsymbol = tradingsymbol
        self.quantity = quantity
        self.discloseqty = discloseqty
        self.price_type = price_type
        self.price = price
        self.trigger_price = trigger_price
        self.retention = retention
        self.remarks = remarks
        self.order_id = None


def get_time(time_string):
    data = time.strptime(time_string, "%d-%m-%Y %H:%M:%S")
    return time.mktime(data)


class ShoonyaApiPy(NorenApi):
    """Multi-broker API wrapper supporting Shoonya, Flattrade, and Simulation modes"""
    
    def __init__(self, broker=None, cred_file=None):
        # Load broker from cred_file if not specified
        if not broker and cred_file:
            broker = self._get_broker_from_creds(cred_file)
        if not broker:
            broker = "shoonya"  # Default
        
        config = get_broker_config(broker)
        
        if is_simulation_mode(broker):
            # Simulation mode - don't connect to any API
            self.broker = broker
            self.broker_name = config["name"]
            self.is_simulation = True
            self.host = None
            self.ws_url = None
            print("Running in SIMULATION mode ({})".format(self.broker_name))
        else:
            # Real broker mode
            self.broker = broker
            self.broker_name = config["name"]
            self.is_simulation = False
            self.host = config["rest"]
            self.ws_url = config["websocket"]
            NorenApi.__init__(self, host=self.host, websocket=self.ws_url)
            print("Connected to {} ({})".format(self.broker_name, self.host))
        
        global api
        api = self

    def _get_broker_from_creds(self, cred_file):
        """Extract broker name from credentials file"""
        if not os.path.exists(cred_file):
            return None
        try:
            with open(cred_file, "r") as f:
                creds = yaml.safe_load(f)
                return creds.get("broker", "shoonya").lower()
        except:
            return None

    def place_basket(self, orders):
        if self.is_simulation:
            return self._simulate_basket(orders)
        
        resp_err = 0
        resp_ok = 0
        result = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(self.place_order, order): order for order in orders}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result.append(future.result())
                    resp_ok += 1
                except Exception as exc:
                    print(exc)
                    resp_err += 1
        return result

    def placeOrder(self, order):
        if self.is_simulation:
            return self._simulate_order(order)
        return NorenApi.place_order(self, buy_or_sell=order.buy_or_sell, product_type=order.product_type,
                            exchange=order.exchange, tradingsymbol=order.tradingsymbol,
                            quantity=order.quantity, discloseqty=order.discloseqty, price_type=order.price_type,
                            price=order.price, trigger_price=order.trigger_price,
                            retention=order.retention, remarks=order.remarks)

    # ========== SIMULATION MODE METHODS ==========
    
    def _simulate_order(self, order):
        """Simulate order execution for paper trading"""
        order_id = "SIM_{}_{}".format(int(time.time()), random.randint(1000, 9999))
        return {
            "stat": "Ok",
            "order_id": order_id,
            "result": "Simulated order",
            "mode": "SIMULATION"
        }
    
    def _simulate_basket(self, orders):
        """Simulate basket order execution"""
        return [self._simulate_order(order) for order in orders]
    
    def get_funds(self):
        """Get account funds - simulation returns dummy data"""
        if self.is_simulation:
            return {
                "stat": "Ok",
                "cash": "100000",
                "margin_used": "0",
                "margin_held": "0",
                "availablecash": "100000",
                "mode": "SIMULATION"
            }
        return super().get_funds()
    
    def get_positions(self):
        """Get open positions - simulation returns empty"""
        if self.is_simulation:
            return []
        return super().get_positions()
    
    def get_order_history(self):
        """Get order history - simulation returns empty"""
        if self.is_simulation:
            return []
        return super().get_order_history()


class FlattradeApiPy(ShoonyaApiPy):
    """Flattrade API - uses ShoonyaApiPy with flattrade broker"""
    def __init__(self):
        super().__init__(broker="flattrade")

# =====================================================
# Flattrade Token Generation Support
# =====================================================
import hashlib
import requests

def get_flattrade_token(api_key: str, request_code: str, api_secret: str) -> str:
    """
    Generate Flattrade token using the OAuth-like flow.
    
    Steps:
    1. Get authorization URL: https://auth.flattrade.in/?app_key=APIKEY
    2. Login and get redirected with request_code
    3. Call this function to exchange for token
    
    Args:
        api_key: Your Flattrade API key
        request_code: One-time code from redirect URL
        api_secret: Your API secret
    
    Returns:
        token: Access token for API calls
    """
    # Generate api_secret hash: SHA256(api_key + request_code + api_secret)
    hash_input = api_key + request_code + api_secret
    hash_signature = hashlib.sha256(hash_input.encode()).hexdigest()
    
    payload = {
        "api_key": api_key,
        "request_code": request_code,
        "api_secret": hash_signature
    }
    
    response = requests.post(
        "https://authapi.flattrade.in/trade/apitoken",
        json=payload
    )
    
    result = response.json()
    
    if result.get("status") == "Ok":
        return result.get("token")
    else:
        raise Exception(f"Flattrade token error: {result.get('emsg', 'Unknown error')}")


def generate_flattrade_auth_url(api_key: str, redirect_url: str = "http://localhost/callback") -> str:
    """
    Generate Flattrade authorization URL for OAuth flow.
    """
    return f"https://auth.flattrade.in/?app_key={api_key}&redirect={redirect_url}"
