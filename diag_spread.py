
import os
import sys
from datetime import date

# Setup Path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(base_dir, 'orbiter'))
sys.path.append(os.path.join(base_dir, 'ShoonyaApi-py'))

from core.broker import BrokerClient

def evaluate_spread(atm_strike, hedge_strike, option_type, symbol='NIFTY'):
    print(f"🕵️  EVALUATING SPREAD: {symbol} {atm_strike}/{hedge_strike} {option_type.upper()}")
    client = BrokerClient('../ShoonyaApi-py/cred.yml')
    if not client.login(): return

    # 1. Find Expiry for weekly options
    expiry = client.resolver._select_expiry(symbol, 'weekly', 'OPTIDX')
    if not expiry:
        print("❌ Could not resolve expiry.")
        return

    print(f"🗓️  Using Expiry: {expiry.isoformat()}")

    # 2. Find contracts
    def find_contract(strike, opt_type):
        rows = client.resolver._get_option_rows(symbol, expiry, 'OPTIDX')
        for row in rows:
            if row.get('strike') == strike and row.get('option_type') == opt_type:
                return row
        return None

    atm_contract = find_contract(atm_strike, option_type)
    hedge_contract = find_contract(hedge_strike, option_type)

    if not atm_contract or not hedge_contract:
        print("❌ Could not find one or both contracts.")
        return

    # 3. Get Quotes
    atm_q = client.api.get_quotes('NFO', atm_contract['token'])
    hdg_q = client.api.get_quotes('NFO', hedge_contract['token'])

    atm_ltp = float(atm_q.get('lp', 0))
    hdg_ltp = float(hdg_q.get('lp', 0))
    lot_size = int(atm_contract.get('lot_size', 0))

    # 4. Calculations
    net_premium = round(atm_ltp - hdg_ltp, 2)
    max_profit = round(net_premium * lot_size, 2)
    max_loss = round(((hedge_strike - atm_strike) * lot_size) - max_profit, 2)
    breakeven = round(atm_strike + net_premium, 2)

    # 5. Margin Calculation
    spread_details = {
        'ok': True, 'expiry': expiry.isoformat(), 'atm_strike': atm_strike, 'hedge_strike': hedge_strike,
        'lot_size': lot_size, 'atm_symbol': atm_contract['tradingsymbol'], 'hedge_symbol': hedge_contract['tradingsymbol'],
        'side': 'PUT' if option_type == 'PE' else 'CALL', 'exchange': 'NFO'
    }
    margin = client.calculate_span_for_spread(spread_details)
    required_margin = margin.get('total_margin', 'N/A')

    # 6. Report
    print("\n--- Bear Call Spread Analysis ---")
    print(f"Action:      SELL {atm_strike} CE @ {atm_ltp} | BUY {hedge_strike} CE @ {hdg_ltp}")
    print(f"Net Premium: {net_premium:.2f} pts (Credit)")
    print(f"Lot Size:    {lot_size}")
    print("---")
    print(f"Max Profit:  ₹{max_profit:,.2f}")
    print(f"Max Loss:    ₹{max_loss:,.2f}")
    print(f"Breakeven:   {breakeven:.2f} (NIFTY must stay below this)")
    print(f"Margin Req:  ₹{required_margin:,.2f}")
    print("---------------------------------")

if __name__ == "__main__":
    # Bear Call Spread
    evaluate_spread(atm_strike=25400, hedge_strike=25500, option_type='CE')
