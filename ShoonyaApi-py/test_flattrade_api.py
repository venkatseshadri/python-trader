"""
Flattrade API Test Class
========================
Reference implementation for Flattrade API calls.
Based on Postman collection.

Usage:
1. Generate auth URL
2. Get request_code from redirect
3. Exchange for token
4. Make API calls
"""

import hashlib
import requests
import json

class FlattradeAPI:
    BASE_URL = "https://piconnect.flattrade.in"
    AUTH_API_URL = "https://authapi.flattrade.in"
    
    def __init__(self, api_key: str, api_secret: str, token: str = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.token = token
        self.session = requests.Session()
    
    def get_auth_url(self, redirect_url: str = "http://localhost:8000/callback") -> str:
        """Generate authorization URL for OAuth flow."""
        return f"{self.AUTH_API_URL}/?app_key={self.api_key}&redirect={redirect_url}"
    
    def generate_hash(self, request_code: str) -> str:
        """Generate SHA-256 hash for token request."""
        hash_input = self.api_key + request_code + self.api_secret
        return hashlib.sha256(hash_input.encode()).hexdigest()
    
    def get_token(self, request_code: str) -> str:
        """Exchange request_code for access token."""
        hash_signature = self.generate_hash(request_code)
        
        payload = {
            "api_key": self.api_key,
            "request_code": request_code,
            "api_secret": hash_signature
        }
        
        response = self.session.post(
            f"{self.AUTH_API_URL}/trade/apitoken",
            json=payload
        )
        
        result = response.json()
        
        if result.get("status") == "Ok":
            self.token = result.get("token")
            return self.token
        else:
            raise Exception("Token error: " + str(result.get('emsg', 'Unknown')))
    
    def _call_api(self, endpoint: str, payload: dict) -> dict:
        """Make authenticated API call."""
        if not self.token:
            raise Exception("No token. Call get_token() first.")
        
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        response = self.session.post(
            f"{self.BASE_URL}{endpoint}",
            json=payload,
            headers=headers
        )
        
        return response.json()
    
    def get_user_details(self) -> dict:
        """Get user profile details."""
        return self._call_api("/UserDetails", {})
    
    def get_limits(self) -> dict:
        """Get trading limits and margin."""
        return self._call_api("/Limits", {})
    
    def get_holdings(self) -> dict:
        """Get holdings."""
        return self._call_api("/Holdings", {})
    
    def get_order_book(self) -> dict:
        """Get order book."""
        return self._call_api("/OrderBook", {})
    
    def get_trade_book(self) -> dict:
        """Get trade book."""
        return self._call_api("/TradeBook", {})
    
    def get_position_book(self) -> dict:
        """Get position book."""
        return self._call_api("/PositionBook", {})
    
    def place_order(self, exchange, tradingsymbol, quantity, buy_or_sell, 
                   order_type="MKT", product_type="MIS", price=0, 
                   trigger_price=0, disclosed_quantity=0) -> dict:
        """Place an order."""
        payload = {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "quantity": quantity,
            "buy_or_sell": buy_or_sell,
            "order_type": order_type,
            "product_type": product_type,
            "price": price,
            "trigger_price": trigger_price,
            "disclosed_quantity": disclosed_quantity
        }
        return self._call_api("/PlaceOrder", payload)
    
    def get_quote(self, exchange, tradingsymbol) -> dict:
        """Get quote for a scrip."""
        return self._call_api("/GetQuotes", {
            "exchange": exchange,
            "tradingsymbol": tradingsymbol
        })
    
    def search_scrip(self, exchange, search_text) -> dict:
        """Search for a scrip."""
        return self._call_api("/SearchScrip", {
            "exchange": exchange,
            "search_text": search_text
        })


if __name__ == "__main__":
    API_KEY = "37d30474def84eb1a0666f1dc2bc0e4f"
    API_SECRET = "YOUR_API_SECRET"
    
    api = FlattradeAPI(API_KEY, API_SECRET)
    
    print("Auth URL:", api.get_auth_url())
    print("Get request_code from redirect URL, then run:")
    print("token = api.get_token('YOUR_REQUEST_CODE')")
    print("print(api.get_user_details())")
