#!/usr/bin/env python3
"""
Margin Checker Utility for Orbiter Trading System

Purpose: Check available margin before taking a trade to ensure sufficient capital.
Can be used in LIVE mode (real broker) or PAPER mode (emulated).

Usage:
    python margin_checker.py --status                   # Check current margin
    python margin_checker.py --symbol NIFTY             # Check if can trade NIFTY
    python margin_checker.py --check-second-trade      # Check if 2nd trade possible
    python margin_checker.py --record-trade NIFTY 1 22000 BUY
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any

# Try to import Shoonya API (for live trading)
try:
    from NorenRestApiPy.NorenApi import NorenApi
    SHOONYA_AVAILABLE = True
except ImportError:
    SHOONYA_AVAILABLE = False
    print("⚠️ Shoonya API not available - running in PAPER mode only")

try:
    import pyotp
    TOTP_AVAILABLE = True
except ImportError:
    TOTP_AVAILABLE = False
    print("⚠️ pyotp not installed - TOTP login unavailable")

# --- CONFIGURATION ---
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'margin_config.json')

DEFAULT_CONFIG = {
    "paper_trade": {
        "initial_capital": 100000,
        "cash": 100000,
        "used_margin": 0,
        "mtm": 0,
        "positions": []
    },
    "broker": {
        "use": "shoonya",
        "shoonya": {
            "user": "",
            "pwd": "",
            "vc": "",
            "apikey": "",
            "imei": "",
            "totp_key": ""
        },
        "flattrade": {
            "user": "",
            "pwd": "",
            "vc": "",
            "apikey": "",
            "imei": ""
        }
    },
    "trading_rules": {
        "max_daily_loss": 5000,
        "warning_at": -4000,
        "profit_lock_at": 5000,
        "risk_after_profit": 2500,
        "per_trade_sl": 2500,
        "cooling_off_minutes": 30
    }
}


class PaperTradeSimulator:
    """Simulates broker margin for paper trading."""
    
    def __init__(self, config: Dict = None):
        self.config = config or DEFAULT_CONFIG['paper_trade']
        self.positions = self.config.get('positions', [])
        self.transaction_log = []
        
    @property
    def cash(self) -> float:
        return self.config['cash']
    
    @property
    def used_margin(self) -> float:
        return self.config['used_margin']
    
    @property
    def mtm(self) -> float:
        return self.config['mtm']
    
    @property
    def net_payin(self) -> float:
        return self.cash + self.used_margin - self.mtm
    
    @property
    def available_margin(self) -> float:
        return self.cash - self.used_margin
    
    def add_position(self, symbol: str, qty: int, entry_price: float, 
                     trade_type: str, strike: int = None, expiry: str = None):
        position = {
            'symbol': symbol,
            'qty': qty,
            'entry_price': entry_price,
            'trade_type': trade_type,
            'strike': strike,
            'expiry': expiry,
            'timestamp': datetime.now().isoformat()
        }
        
        margin_required = self._estimate_margin(position)
        position['margin_required'] = margin_required
        self.positions.append(position)
        self.config['used_margin'] += margin_required
        
        self.transaction_log.append({
            'action': 'OPEN',
            'position': position,
            'timestamp': datetime.now().isoformat()
        })
        
        self._save_state()
        return margin_required
    
    def close_position(self, symbol: str, exit_price: float, qty: int = None):
        for pos in self.positions:
            if pos['symbol'] == symbol:
                qty_to_close = qty or pos['qty']
                pnl = (exit_price - pos['entry_price']) * qty_to_close
                
                self.config['used_margin'] -= pos['margin_required']
                self.config['mtm'] += pnl
                
                self.transaction_log.append({
                    'action': 'CLOSE',
                    'position': pos,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'timestamp': datetime.now().isoformat()
                })
                
                if qty_to_close >= pos['qty']:
                    self.positions.remove(pos)
                else:
                    pos['qty'] -= qty_to_close
                    pos['margin_required'] = (pos['margin_required'] / pos['qty']) * (pos['qty'] - qty_to_close)
                
                self._save_state()
                return pnl
        return 0
    
    def _estimate_margin(self, position: Dict) -> float:
        symbol = position['symbol']
        qty = position['qty']
        strike = position.get('strike')
        
        if 'NIFTY' in symbol.upper():
            base_margin = 150000
            if strike:
                strike_diff = abs(strike - 22000) // 100
                base_margin += strike_diff * 5000
            return base_margin * qty
            
        elif 'BANKNIFTY' in symbol.upper():
            base_margin = 300000
            if strike:
                strike_diff = abs(strike - 48000) // 100
                base_margin += strike_diff * 10000
            return base_margin * qty
            
        elif 'SENSEX' in symbol.upper():
            base_margin = 400000
            return base_margin * qty
            
        else:
            notional = position['entry_price'] * qty * 50
            return max(50000, notional * 0.20)
    
    def _save_state(self):
        state_file = os.path.join(os.path.dirname(__file__), 'paper_trade_state.json')
        with open(state_file, 'w') as f:
            json.dump({
                'config': self.config,
                'positions': self.positions,
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    @classmethod
    def load_state(cls) -> 'PaperTradeSimulator':
        state_file = os.path.join(os.path.dirname(__file__), 'paper_trade_state.json')
        if os.path.exists(state_file):
            with open(state_file, 'r') as f:
                state = json.load(f)
                return cls(state.get('config', {}))
        return cls()


class MarginChecker:
    def __init__(self, paper_trade: bool = True):
        self.paper_trade = paper_trade
        self.config = self._load_config()
        
        if paper_trade:
            self.simulator = PaperTradeSimulator.load_state()
        else:
            self.simulator = None
            self.api = None
    
    def _load_config(self) -> Dict:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return DEFAULT_CONFIG
    
    def connect_broker(self) -> bool:
        if self.paper_trade:
            print("📄 Running in PAPER TRADE mode")
            return True
        
        if not SHOONYA_AVAILABLE:
            print("❌ Shoonya API not available")
            return False
        
        broker_config = self.config['broker']['shoonya']
        
        if not all([broker_config.get('user'), broker_config.get('totp_key')]):
            print("❌ Broker credentials not configured")
            print("   Edit margin_config.json to add credentials")
            return False
        
        try:
            self.api = NorenApi()
            totp = pyotp.TOTP(broker_config['totp_key'])
            current_otp = totp.now()
            
            ret = self.api.login(
                userid=broker_config['user'],
                password=broker_config['pwd'],
                twoFA=current_otp,
                vendor_code=broker_config['vc'],
                api_secret=broker_config['apikey'],
                imei=broker_config['imei']
            )
            
            if ret and ret.get('stat') == 'Ok':
                print(f"✅ Login successful! Welcome {ret.get('uname')}")
                return True
            else:
                print(f"❌ Login failed: {ret.get('emsg') if ret else 'No response'}")
                return False
                
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def get_limits(self) -> Optional[Dict]:
        if self.paper_trade:
            return {
                'cash': self.simulator.cash,
                'used_margin': self.simulator.used_margin,
                'mtm': self.simulator.mtm,
                'available_margin': self.simulator.available_margin,
                'net_payin': self.simulator.net_payin
            }
        
        if not self.api:
            return None
        
        try:
            limits = self.api.get_limits()
            if limits and limits.get('stat') == 'Ok':
                return {
                    'cash': float(limits.get('cash', 0)),
                    'used_margin': float(limits.get('marginused', 0)),
                    'mtm': float(limits.get('ur_pnl', 0)),
                    'available_margin': float(limits.get('cash', 0)) - float(limits.get('marginused', 0))
                }
        except Exception as e:
            print(f"❌ Error fetching limits: {e}")
        
        return None
    
    def check_margin_for_trade(self, symbol: str, qty: int, estimated_premium: float = 0) -> Dict:
        limits = self.get_limits()
        if not limits:
            return {'allowed': False, 'reason': 'Could not fetch limits'}
        
        available = limits['available_margin']
        margin_required = self._estimate_margin_required(symbol, qty, estimated_premium)
        
        if available >= margin_required:
            return {
                'allowed': True,
                'available': available,
                'required': margin_required,
                'remaining_after_trade': available - margin_required
            }
        else:
            return {
                'allowed': False,
                'available': available,
                'required': margin_required,
                'shortfall': margin_required - available
            }
    
    def check_second_trade(self, first_trade_symbol: str = None) -> Dict:
        """Check if a second trade can be taken based on current margin."""
        limits = self.get_limits()
        if not limits:
            return {'allowed': False, 'reason': 'Could not fetch limits'}
        
        rules = self.config['trading_rules']
        available = limits['available_margin']
        
        if first_trade_symbol:
            first_margin = self._estimate_margin_required(first_trade_symbol, 1)
            remaining = available - first_margin
        else:
            remaining = available
        
        current_mtm = limits.get('mtm', 0)
        
        if current_mtm >= rules['profit_lock_at']:
            max_risk = rules['risk_after_profit']
            status = "PROFIT LOCKED - Reducing risk to ₹2,500"
        elif current_mtm <= -rules['max_daily_loss']:
            return {
                'allowed': False,
                'reason': f"Daily loss limit hit (₹{current_mtm:.0f} / -₹{rules['max_daily_loss']})"
            }
        elif current_mtm <= rules['warning_at']:
            status = "WARNING: Close to daily loss limit"
            max_risk = rules['per_trade_sl']
        else:
            status = "Normal"
            max_risk = rules['per_trade_sl']
        
        if remaining >= max_risk:
            return {
                'allowed': True,
                'available': available,
                'remaining_after_first': remaining,
                'can_risk': max_risk,
                'status': status,
                'mtm': current_mtm
            }
        else:
            return {
                'allowed': False,
                'available': available,
                'remaining_after_first': remaining,
                'required': max_risk,
                'shortfall': max_risk - remaining,
                'reason': f"Insufficient margin (need ₹{max_risk:.0f}, have ₹{remaining:.0f})",
                'status': status,
                'mtm': current_mtm
            }
    
    def _estimate_margin_required(self, symbol: str, qty: int, premium: float = 0) -> float:
        symbol = symbol.upper()
        
        if 'NIFTY' in symbol:
            return 150000 * qty
        elif 'BANKNIFTY' in symbol:
            return 300000 * qty
        elif 'SENSEX' in symbol:
            return 400000 * qty
        else:
            return max(50000, premium * 50 * qty * 0.20)
    
    def print_status(self):
        print("\n" + "="*50)
        print("📊 MARGIN STATUS")
        print("="*50)
        
        limits = self.get_limits()
        if not limits:
            print("❌ Could not fetch margin status")
            return
        
        print(f"💰 Cash Available:   ₹{limits['cash']:,.0f}")
        print(f"📌 Used Margin:      ₹{limits['used_margin']:,.0f}")
        print(f"📈 MTM (Unrealized): ₹{limits['mtm']:,.0f}")
        print(f"✅ Available Margin: ₹{limits['available_margin']:,.0f}")
        
        if self.paper_trade and self.simulator:
            print(f"📋 Open Positions:   {len(self.simulator.positions)}")
            for pos in self.simulator.positions:
                print(f"   - {pos['symbol']}: {pos['trade_type']} {pos['qty']} @ ₹{pos['entry_price']}")
        
        print("="*50)
        
        second = self.check_second_trade()
        print(f"\n🔄 SECOND TRADE CHECK:")
        if second['allowed']:
            print(f"   ✅ ALLOWED - Can risk up to ₹{second.get('can_risk', 0):,.0f}")
        else:
            print(f"   ❌ NOT ALLOWED - {second.get('reason', 'Unknown')}")
        
        print(f"   Status: {second.get('status', 'N/A')}")
        print(f"   MTM: ₹{second.get('mtm', 0):,.0f}")
        print()
    
    def record_trade(self, symbol: str, qty: int, price: float, trade_type: str):
        if not self.paper_trade:
            print("⚠️ Can only record trades in paper trade mode")
            return
        
        margin = self.simulator.add_position(symbol, qty, price, trade_type)
        print(f"✅ Recorded {trade_type} {qty} {symbol} @ ₹{price}")
        print(f"   Margin required: ₹{margin:,.0f}")
        self.print_status()


def main():
    parser = argparse.ArgumentParser(description='Margin Checker Utility')
    parser.add_argument('--paper-trade', action='store_true', help='Use paper trade mode')
    parser.add_argument('--live', action='store_true', help='Use live broker')
    parser.add_argument('--status', action='store_true', help='Show current margin status')
    parser.add_argument('--symbol', type=str, help='Check margin for specific symbol')
    parser.add_argument('--qty', type=int, default=1, help='Quantity for symbol check')
    parser.add_argument('--premium', type=float, default=0, help='Estimated premium')
    parser.add_argument('--check-second-trade', action='store_true', help='Check if 2nd trade allowed')
    parser.add_argument('--record-trade', nargs=4, metavar=('SYMBOL', 'QTY', 'PRICE', 'TYPE'),
                        help='Record trade: SYMBOL QTY PRICE BUY|SELL')
    parser.add_argument('--configure', action='store_true', help='Configure broker credentials')
    parser.add_argument('--init', action='store_true', help='Initialize paper trade with ₹1 lakh')
    
    args = parser.parse_args()
    
    # Determine mode
    paper_trade = args.paper_trade or not args.live
    
    checker = MarginChecker(paper_trade=paper_trade)
    
    if args.init:
        # Initialize with default ₹1 lakh
        sim = PaperTradeSimulator(DEFAULT_CONFIG['paper_trade'])
        sim._save_state()
        print("✅ Initialized paper trade with ₹1,00,000 capital")
        return
    
    if args.configure:
        print("Edit margin_config.json to add broker credentials")
        return
    
    if args.status:
        checker.print_status()
        return
    
    if args.check_second_trade:
        result = checker.check_second_trade()
        print(json.dumps(result, indent=2))
        return
    
    if args.symbol:
        result = checker.check_margin_for_trade(args.symbol, args.qty, args.premium)
        print(json.dumps(result, indent=2))
        return
    
    if args.record_trade:
        symbol, qty, price, trade_type = args.record_trade
        checker.record_trade(symbol, int(qty), float(price), trade_type.upper())
        return
    
    # Default: show status
    checker.print_status()


if __name__ == "__main__":
    main()
