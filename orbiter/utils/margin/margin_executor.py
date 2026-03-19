"""
Margin-Aware Order Executor Wrapper

This module wraps the OrderExecutor to add margin checking before trade execution.
Works in both paper-trade and live modes.

Usage:
    from orbiter.utils.margin.margin_executor import MarginAwareExecutor
    
    executor = MarginAwareExecutor(api, logger, execution_policy, paper_trade=True)
"""

import os
import logging
from typing import Dict, Any

from orbiter.core.engine.action.interfaces import OrderExecutorInterface
from orbiter.utils.margin.margin_manager import MarginManager


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
                 paper_trade: bool = True, project_root: str = None):
        self.api = api
        self.logger = logger
        self.execution_policy = execution_policy or {}
        self.paper_trade = paper_trade
        self.project_root = project_root
        
        self.margin_manager = MarginManager(api=api, paper_trade=paper_trade, project_root=project_root)
        self.logger.info(f"[MARGIN] MarginAwareExecutor initialized (paper_trade={paper_trade})")
    
    def get_limits(self) -> Dict:
        """Get trading limits from margin manager."""
        return self.margin_manager.get_limits()
    
    def check_margin(self, symbol: str, qty: int, premium: float = 0) -> Dict:
        """Check if margin is available for the trade."""
        return self.margin_manager.check_margin(symbol, qty, premium)
    
    def _check_margin(self, symbol: str, qty: int, premium: float = 0) -> Dict[str, Any]:
        """Check if margin is available for the trade."""
        result = self.margin_manager.check_margin(symbol, qty, premium)
        
        if not result.get('allowed'):
            self.logger.warning(f"[MARGIN] ⛔ MARGIN BLOCK: {symbol} qty={qty} - need ₹{result.get('required', 0)} but only ₹{result.get('available', 0)} available")
        
        return result
    
    def _log_margin_check(self, symbol: str, qty: int, result: Dict):
        """Log margin check result."""
        self.logger.info(f"[MARGIN] Check: {symbol} qty={qty} allowed={result.get('allowed')} available={result.get('available')} required={result.get('required')}")
    
    def _record_paper_trade(self, symbol: str, qty: int, price: float, trade_type: str):
        """Record a paper trade for margin tracking."""
        self.margin_manager.record_trade(symbol, qty, price, trade_type)
    
    def _get_margin_status(self) -> Dict:
        """Get current margin status."""
        return self.margin_manager.get_limits()
    
    def place_future_order(self, future_details: Dict[str, Any], side: str, execute: bool, 
                          product_type: str, price_type: str) -> Dict[str, Any]:
        """Execute future order with margin checking."""
        tsym = future_details['tsym']
        lot = future_details['lot_size']
        
        if execute:
            margin_result = self._check_margin(tsym, lot)
            
            if not margin_result['allowed']:
                self.logger.warning(f"[MARGIN] ⛔ MARGIN BLOCK: {tsym} qty={lot}")
                return {**future_details, 'ok': False, 'reason': 'margin_blocked', 'margin': margin_result}
        
        from orbiter.utils.margin.margin_executor_base import ExecutorBase
        
        base = ExecutorBase(self.api, self.execution_policy)
        result = base.place_future_order(future_details, side, execute, product_type, price_type)
        
        if execute and result.get('ok'):
            self._record_paper_trade(tsym, lot, result.get('price', 0), f"future_{side}")
        
        return result
    
    def place_option_order(self, option_details: Dict[str, Any], side: str, execute: bool, 
                          product_type: str, price_type: str) -> Dict[str, Any]:
        """Execute option order with margin checking."""
        tsym = option_details.get('tsym', option_details.get('symbol'))
        lot = option_details.get('lot_size', 1)
        premium = option_details.get('premium', 0)
        
        if execute:
            margin_result = self._check_margin(tsym, lot, premium)
            
            if not margin_result['allowed']:
                self.logger.warning(f"[MARGIN] ⛔ MARGIN BLOCK: {tsym} qty={lot} premium={premium}")
                return {**option_details, 'ok': False, 'reason': 'margin_blocked', 'margin': margin_result}
        
        from orbiter.utils.margin.margin_executor_base import ExecutorBase
        
        base = ExecutorBase(self.api, self.execution_policy)
        result = base.place_option_order(option_details, side, execute, product_type, price_type)
        
        if execute and result.get('ok'):
            self._record_paper_trade(tsym, lot, premium, f"option_{side}")
        
        return result
    
    def place_spread(self, spread: Dict[str, Any], execute: bool, product_type: str, 
                    price_type: str) -> Dict[str, Any]:
        """Execute spread order with margin checking."""
        atm_sym = spread.get('atm_symbol')
        hedge_sym = spread.get('hedge_symbol')
        lot = spread.get('lot_size', 1)
        
        if execute:
            margin_result = self._check_margin(atm_sym, lot)
            
            if not margin_result['allowed']:
                self.logger.warning(f"[MARGIN] ⛔ MARGIN BLOCK: spread {atm_sym}/{hedge_sym} qty={lot}")
                return {**spread, 'ok': False, 'reason': 'margin_blocked', 'margin': margin_result}
        
        from orbiter.utils.margin.margin_executor_base import ExecutorBase
        
        base = ExecutorBase(self.api, self.execution_policy)
        result = base.place_spread(spread, execute, product_type, price_type)
        
        if execute and result.get('ok'):
            self._record_paper_trade(atm_sym, lot, 0, "spread")
        
        return result
    
    def place_future_order_full(self, symbol: str, exchange: str, side: str, execute: bool, 
                                product_type: str, price_type: str, token: str = None, **kwargs) -> Dict:
        """Place future order with full resolution - not implemented in margin executor."""
        return {'ok': False, 'reason': 'use_future_executor'}
