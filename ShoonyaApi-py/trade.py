"""
shoonya_dummy_trade.py

- Logs into Shoonya using ShoonyaApiPy
- Places a small market BUY order (dummy trade)
"""

import logging
from api_helper import ShoonyaApiPy  # comes from ShoonyaApi-Py package

# Enable debug logs if you want to see request/response details
logging.basicConfig(level=logging.INFO)


def main():
    # TODO: replace these with your real details
    user_id = "FA333160"
    password = "Taknev80$$$"          # plain password; ShoonyaApiPy will handle hashing as per library
    factor2 = "186215"      # e.g. DOB (DD-MM-YYYY) or PAN as configured
    vendor_code = "FA333160_U"    # provided by Shoonya/Finvasia
    api_secret = "cb4299f4cd849a4983d5ad50322d8e2d"      # app key / secret key
    imei = "C0FJFG7WW7"      # any unique string for your machine

    # Create API object
    api = ShoonyaApiPy()

    # Login
    login_result = api.login(
        userid=user_id,
        password=password,
        twoFA=factor2,
        vendor_code=vendor_code,
        api_secret=api_secret,
        imei=imei,
    )
    print("Login response:", login_result)

    if not login_result or login_result.get("stat") != "Ok":
        print("Login failed, aborting.")
        return

    # ---- Dummy trade parameters ----
    # Very small market order on NSE; change symbol/exchange/product as needed
    exchange = "NSE"
    tradingsymbol = "INFY-EQ"   # example equity symbol on NSE [file:2]
    quantity = 1                # dummy small quantity
    product_type = "C"          # delivery/cash product as per prarr [file:2]
    price_type = "MKT"          # market order [file:2]

    # Place market BUY order
    order_resp = api.place_order(
        buy_or_sell="B",          # B -> BUY [file:2]
        product_type=product_type,
        exchange=exchange,
        tradingsymbol=tradingsymbol,
        quantity=quantity,
        discloseqty=0,
        price_type=price_type,
        price=0,                  # 0 for MKT [file:2]
        trigger_price=None,
        retention="DAY",          # DAY / IOC / EOS [file:2]
        amo="NO",
        remarks="dummy_order_001",
    )

    print("Order response:", order_resp)

    # Optional: logout at the end
    try:
        logout_resp = api.logout()
        print("Logout response:", logout_resp)
    except Exception as e:
        print("Logout failed:", e)


if __name__ == "__main__":
    main()
