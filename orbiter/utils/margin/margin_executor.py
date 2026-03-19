"""
Margin-Aware Order Executor Wrapper

This module wraps the OrderExecutor to add margin checking before trade execution.
Works in both paper-trade and live modes.

Usage:
    from orbiter.utils.margin.margin_executor import MarginAwareExecutor
    
    # Replace OrderExecutor with MarginAwareExecutor in your code
    executor = MarginAwareExecutor(api, logger, execution_policy)
"""

import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Import the interface
from orbiter.core.engine.action.interfaces import OrderExecutorInterface

# Import margin checker
MARGIN_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, MARGIN_DIR)

try:
    from margin_checker import MarginChecker, PaperTradeSimulator
    MARGIN_CHECKER_AVAILABLE = True
except ImportError:
    MARGIN_CHECKER_AVAILABLE = False
    print("[MARGIN] Warning: margin_checker not available")


class MarginAwareExecutor(OrderExecutorInterface):
    """
    OrderExecutor with integrated margin checking.
    
    In PAPER_TRADE mode:
    - Tracks margin usage in paper_trade_state.json
    - Logs all margin checks to margin_log.txt
    - Blocks trades if insufficient margin
    
    In LIVE mode:
    - Checks actual broker margin (if available)
    - Still logs margin checks for tracking
    """
    
    def __init__(self, api, logger: logging.Logger, execution_policy: Dict[str, Any] = None, 
                 paper_trade: bool = True):
        self.api = api
        self.logger = logger
        self.execution_policy = execution_policy or {}
        self.paper_trade = paper_trade
        self.margin_checker = None
        
        if MARGIN_CHECKER_AVAILABLE:
            self.margin_checker = MarginChecker(paper_trade=paper_trade)
            self.logger.info(f"[MARGIN] MarginAwareExecutor initialized (paper_trade={paper_trade})")
        else:
            self.logger.warning("[MARGIN] Margin checker not available - trades will proceed without margin checks")
    
    def _check_margin(self, symbol: str, qty: int, premium: float = 0) -> Dict[str, Any]:
        """
        Check if margin is available for the trade.
        
        Returns:
            dict with keys: allowed (bool), reason (str), available (float), required (float)
        """
        if not self.margin_checker:
            return {'allowed': True, 'reason': 'margin_checker_not_available'}
        
        result = self.margin_checker.check_margin_for_trade(symbol, qty, premium)
        
        # Log the check
        self._log_margin_check(symbol, qty, result)
        
        return result
    
    def _log_margin_check(self, symbol: str, qty: int, result: Dict):
        """Log margin check to file."""
        log_file = os.path.join(MARGIN_DIR, 'margin_log.txt')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        status = "✅ ALLOWED" if result['allowed'] else "❌ BLOCKED"
        log_line = f"[{timestamp}] {status} | {symbol} x{qty} | Available: Rs{result.get('available', 0):,.0f} | Required: Rs{result.get('required', 0):,.0f}"
        
        if not result['allowed']:
            log_line += f" | Reason: {result.get('reason', 'N/A')}"
        
        log_line += "\n"
        
        try:
            with open(log_file, 'a') as f:
                f.write(log_line)
        except Exception as e:
            self.logger.error(f"[MARGIN] Failed to write log: {e}")
        
        # Also log to logger
        self.logger.info(f"[MARGIN] {status} for {symbol} x{qty}")
    
    def _record_paper_trade(self, symbol: str, qty: int, price: float, trade_type: str):
        """Record paper trade and update margin usage."""
        if not self.paper_trade or not self.margin_checker:
            return
        
        try:
            self.margin_checker.record_trade(symbol, qty, price, trade_type)
            self.logger.info(f"[MARGIN] Recorded paper trade: {trade_type} {symbol} x{qty} @ Rs{price}")
        except Exception as e:
            self.logger.error(f"[MARGIN] Failed to record paper trade: {e}")
    
    def _get_margin_status(self) -> Dict:
        """Get current margin status."""
        if not self.margin_checker:
            return {}
        return self.margin_checker.get_limits()
    
    def place_future_order(self, future_details: Dict[str, Any], side: str, execute: bool, 
                          product_type: str, price_type: str) -> Dict[str, Any]:
        """Execute future order with margin checking."""
        tsym = future_details['tsym']
        lot = future_details['lot_size']
        
        # Check margin BEFORE executing (only in execute mode)
        if execute:
            margin_result = self._check_margin(tsym, lot)
            
            if not margin_result['allowed']:
                self.logger.warning(f"[MARGIN] BLOCKED: {tsym} - {margin_result.get('reason', 'Insufficient margin')}")
                return {
                    'ok': False, 
                    'reason': f"margin_check_failed: {margin_result.get('reason', 'Insufficient margin')}",
                    'margin_check': margin_result
                }
            
            # Get current margin status for logging
            status = self._get_margin_status()
            self.logger.info(f"[MARGIN] Proceeding: {tsym} | Available: Rs{status.get('available_margin', 0):,.0f}")
        
        # Execute the actual order
        result = super().place_future_order(future_details, side, execute, product_type, price_type)
        
        # Record paper trade if successful
        if execute and result.get('ok') and self.paper_trade:
            trade_type = 'BUY' if side == 'B' else 'SELL'
            # Try to get execution price from result
            price = result.get('resp', {}).get('lp', 0) or result.get('limit_price', 0)
            if price:
                self._record_paper_trade(tsym, lot, price, trade_type)
        
        return result
    
    def place_spread(self, spread: Dict[str, Any], execute: bool, product_type: str, 
                    price_type: str) -> Dict[str, Any]:
        """Execute spread order with margin checking."""
        atm_sym = spread['atm_symbol']
        lot = spread['lot_size']
        
        # Check margin BEFORE executing (only in execute mode)
        if execute:
            margin_result = self._check_margin(atm_sym, lot)
            
            if not margin_result['allowed']:
                self.logger.warning(f"[MARGIN] BLOCKED: spread {atm_sym} - {margin_result.get('reason', 'Insufficient margin')}")
                return {
                    'ok': False, 
                    'reason': f"margin_check_failed: {margin_result.get('reason', 'Insufficient margin')}",
                    'margin_check': margin_result
                }
            
            status = self._get_margin_status()
            self.logger.info(f"[MARGIN] Proceeding: spread {atm_sym} | Available: Rs{status.get('available_margin', 0):,.0f}")
        
        # Execute the actual spread
        result = super().place_spread(spread, execute, product_type, price_type)
        
        # Record paper trades if successful
        if execute and result.get('ok') and self.paper_trade:
            # Get prices from result
            atm_price = result.get('atm_resp', {}).get('lp', 0) or 0
            hedge_price = result.get('hedge_resp', {}).get('lp', 0) or 0
            
            if atm_price:
                self._record_paper_trade(atm_sym, lot, atm_price, 'SELL')  # Sell ATM
            if hedge_price:
                hedge_sym = spread.get('hedge_symbol')
                self._record_paper_trade(hedge_sym, lot, hedge_price, 'BUY')  # Buy Hedge
        
        return result
    
    def place_option_order(self, option_details: Dict[str, Any], side: str, execute: bool, 
                          product_type: str, price_type: str) -> Dict[str, Any]:
        """Execute single option order with margin checking."""
        tsym = option_details.get('tsym', option_details.get('symbol'))
        lot = option_details.get('lot_size', 1)
        
        # Check margin BEFORE executing (only in execute mode)
        if execute:
            margin_result = self._check_margin(tsym, lot)
            
            if not margin_result['allowed']:
                self.logger.warning(f"[MARGIN] BLOCKED: option {tsym} - {margin_result.get('reason', 'Insufficient margin')}")
                return {
                    'ok': False, 
                    'reason': f"margin_check_failed: {margin_result.get('reason', 'Insufficient margin')}",
                    'margin_check': margin_result
                }
        
        # Get price and execute
        price = 0
        if price_type == 'LMT':
            try:
                exch = option_details.get('exchange', 'NFO')
                q = self.api.get_quotes(exchange=exch, token=option_details.get('token'))
                if q:
                    price = float(q.get('lp', 0))
            except:
                pass
        
        # Log paper trade
        if not execute or not self.margin_checker:
            trade_type = "BUY" if side == 'B' else "SELL"
            self._record_paper_trade(tsym, lot, price, trade_type)
        
        return {**option_details, 'ok': True, 'executed': execute}


def get_margin_status_cli():
    """CLI to get margin status."""
    if not MARGIN_CHECKER_AVAILABLE:
        print("❌ Margin checker not available")
        return
    
    checker = MarginChecker(paper_trade=True)
    checker.print_status()


if __name__ == "__main__":
    get_margin_status_cli()
