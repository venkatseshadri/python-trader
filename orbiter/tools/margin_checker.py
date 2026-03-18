#!/usr/bin/env python3
"""
Margin Checker Utility
Check available margin before each trade, and simulate margin impact for paper trades.

Usage:
    # Check current margin
    python -m orbiter.tools.margin_checker

    # Check margin with simulated trade (paper trade impact)
    python -m orbiter.tools.margin_checker --symbol CRUDEOILM --quantity 1 --price 5200

    # Check margin with simulated trade for multiple positions
    python -m orbiter.tools.margin_checker --simulate
"""
import sys
import os
import argparse
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orbiter.core.broker import BrokerClient


def load_credentials():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cred_path = os.path.join(project_root, 'ShoonyaApi-py', 'cred.yml')
    if not os.path.exists(cred_path):
        print(f"❌ Credentials file not found: {cred_path}")
        return None
    return cred_path


def print_margin_report(limits, title="CURRENT MARGIN STATUS"):
    if not limits:
        print("❌ Could not fetch margin details")
        return

    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")
    print(f"  💰 Liquid Cash:      ₹{limits['liquid_cash']:,.2f}")
    print(f"  🏦 Collateral:       ₹{limits['collateral_value']:,.2f}")
    print(f"  📊 Total Power:      ₹{limits['total_power']:,.2f}")
    print(f"  📉 Margin Used:      ₹{limits['margin_used']:,.2f}")
    print(f"  ✅ AVAILABLE:       ₹{limits['available']:,.2f}")
    print(f"{'='*50}\n")


def get_mc_margin_per_lot(symbol, exchange='MCX'):
    """Get approximate margin required per lot for MCX symbols."""
    margin_map = {
        'CRUDEOILM': 45000,
        'NATURALGAS': 15000,
        'NATGASMINI': 6000,
        'GOLDM': 80000,
        'GOLDPETAL': 12000,
        'SILVERM': 120000,
        'SILVERMIC': 12000,
        'COPPER': 25000,
        'ZINCMINI': 7000,
        'LEADMINI': 12000,
        'ALUMINI': 8000,
    }
    return margin_map.get(symbol, 25000)


def simulate_trade_impact(limits, symbol, quantity, price, exchange='MCX'):
    """Simulate the margin impact of a trade."""
    lot_size = 1
    if symbol == 'CRUDEOILM':
        lot_size = 10
    elif symbol == 'NATURALGAS':
        lot_size = 1250
    elif symbol == 'NATGASMINI':
        lot_size = 250
    elif symbol == 'SILVERM':
        lot_size = 5
    elif symbol == 'SILVERMIC':
        lot_size = 1
    
    total_value = price * quantity * lot_size
    # Approximate margin: 10-15% of notional for MCX futures
    margin_needed = max(get_mc_margin_per_lot(symbol), total_value * 0.12)
    
    available_after = limits['available'] - margin_needed
    
    print(f"\n{'='*50}")
    print(f"  SIMULATED TRADE IMPACT")
    print(f"{'='*50}")
    print(f"  Symbol:            {symbol}")
    print(f"  Quantity:          {quantity} lot(s)")
    print(f"  Price:             ₹{price:,.2f}")
    print(f"  Notional Value:    ₹{total_value:,.2f}")
    print(f"  Est. Margin:       ₹{margin_needed:,.2f}")
    print(f"{'-'*50}")
    print(f"  Available Before:  ₹{limits['available']:,.2f}")
    print(f"  Margin Needed:     ₹{margin_needed:,.2f}")
    print(f"  Available After:   ₹{available_after:,.2f}")
    
    if available_after < 0:
        print(f"\n  ⚠️  INSUFFICIENT MARGIN! Trade would exceed available funds.")
        print(f"      Shortfall: ₹{abs(available_after):,.2f}")
    else:
        print(f"\n  ✅ MARGIN OK - Can take this trade!")
        # Check if can take another trade of same size
        additional_trades = int(available_after / margin_needed)
        print(f"      Could take ~{additional_trades} more trade(s) of similar size")
    print(f"{'='*50}\n")
    
    return available_after


def check_positions(client):
    """Check current open positions."""
    positions = client.get_positions()
    if not positions:
        print("📭 No open positions")
        return []
    
    print(f"\n📊 OPEN POSITIONS ({len(positions)}):")
    print("-" * 60)
    total_mtm = 0
    for p in positions:
        sym = p.get('tsym', p.get('symbol', 'UNKNOWN'))
        qty = int(p.get('netqty', 0))
        mtm = float(p.get('ur_pnl', 0))
        total_mtm += mtm
        status = "LONG" if qty > 0 else "SHORT" if qty < 0 else "FLAT"
        print(f"  {sym:<20} | Qty: {qty:>4} | MTM: ₹{mtm:>10,.2f} | {status}")
    
    print("-" * 60)
    print(f"  TOTAL MTM: ₹{total_mtm:,.2f}\n")
    return positions


def check_orders(client):
    """Check pending orders."""
    orders = client.get_orders()
    if not orders:
        print("📭 No pending orders")
        return []
    
    pending = [o for o in orders if o.get('ordstatus') in ('OPEN', 'TRIGGER_PENDING')]
    if not pending:
        print("📭 No pending orders")
        return []
    
    print(f"\n📋 PENDING ORDERS ({len(pending)}):")
    for o in pending:
        sym = o.get('tsym', o.get('symbol', 'UNKNOWN'))
        qty = o.get('qty', '?')
        price = o.get('price', 'MKT')
        status = o.get('ordstatus', '?')
        print(f"  {sym:<20} | Qty: {qty} | Price: {price} | {status}")
    print()
    return pending


def main():
    parser = argparse.ArgumentParser(description='Check available margin for trading')
    parser.add_argument('--symbol', type=str, help='Symbol to simulate')
    parser.add_argument('--quantity', type=int, default=1, help='Quantity (lots)')
    parser.add_argument('--price', type=float, help='Price for simulation')
    parser.add_argument('--simulate', action='store_true', help='Show trade simulation')
    parser.add_argument('--positions', action='store_true', help='Show open positions')
    parser.add_argument('--orders', action='store_true', help='Show pending orders')
    parser.add_argument('--exchange', type=str, default='MCX', help='Exchange (MCX/NFO)')
    
    args = parser.parse_args()
    
    cred_path = load_credentials()
    if not cred_path:
        return
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print("🔗 Connecting to broker...")
    client = BrokerClient(project_root=project_root, config_path=cred_path)
    
    if not client.login():
        print("❌ Login failed")
        return
    
    print("✅ Connected!\n")
    
    # Get current limits
    limits = client.get_limits()
    print_margin_report(limits)
    
    # Show positions if requested
    if args.positions:
        check_positions(client)
    
    # Show pending orders if requested
    if args.orders:
        check_orders(client)
    
    # Simulate trade if requested
    if args.symbol and args.price:
        simulate_trade_impact(limits, args.symbol, args.quantity, args.price, args.exchange)
    elif args.simulate:
        print("⚠️  Use --symbol and --price to simulate a trade")
        print("    Example: --symbol CRUDEOILM --price 5200 --quantity 1")


if __name__ == "__main__":
    main()
