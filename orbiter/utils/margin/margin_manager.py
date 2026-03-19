# orbiter/utils/margin/margin_manager.py
"""
Margin Manager - Unified interface for margin operations.

Handles:
- Fetching limits from broker or paper simulation
- Checking margin before trades (delegates to MarginChecker)
- Recording trades for paper trading (delegates to MarginChecker)

Uses MarginChecker for actual margin calculations.
"""

import logging
from typing import Dict, Optional


class MarginManager:
    """Manages margin operations for both paper and live trading."""
    
    def __init__(self, api=None, paper_trade: bool = True, project_root: str = None):
        self.api = api
        self.paper_trade = paper_trade
        self.project_root = project_root
        self.logger = logging.getLogger(f"margin_manager")
        
        self._margin_checker = None
        self._init_margin_checker()
    
    def _init_margin_checker(self):
        """Initialize margin checker."""
        try:
            from orbiter.utils.margin.margin_checker import MarginChecker
            self._margin_checker = MarginChecker(paper_trade=self.paper_trade)
            self.logger.info(f"[MARGIN] MarginManager initialized (paper_trade={self.paper_trade})")
        except ImportError as e:
            self.logger.warning(f"[MARGIN] MarginChecker not available: {e}")
    
    def get_limits(self) -> Dict:
        """Get trading limits (available margin, used, etc)."""
        if self._margin_checker:
            limits = self._margin_checker.get_limits()
            if limits:
                return limits
        
        if not self.paper_trade and self.api:
            try:
                res = self.api.get_limits()
                if res and res.get('stat') == 'Ok':
                    cash = float(res.get('cash', 0))
                    collateral = float(res.get('collateral', 0))
                    used = float(res.get('marginused', 0))
                    total_power = cash + collateral
                    return {
                        'liquid_cash': cash,
                        'collateral_value': collateral,
                        'margin_used': used,
                        'total_power': total_power,
                        'available': total_power - used,
                        'payin': float(res.get('payin', 0))
                    }
            except Exception as e:
                self.logger.error(f"[MARGIN] Error fetching limits: {e}")
        
        return {
            'liquid_cash': 0,
            'collateral_value': 0,
            'margin_used': 0,
            'total_power': 0,
            'available': 0,
            'payin': 0
        }
    
    def check_margin(self, symbol: str, qty: int, premium: float = 0) -> Dict:
        """Check if sufficient margin is available for a trade."""
        if self._margin_checker:
            return self._margin_checker.check_margin_for_trade(symbol, qty, premium)
        
        limits = self.get_limits()
        required = premium * qty
        
        return {
            'allowed': limits.get('available', 0) >= required,
            'required': required,
            'available': limits.get('available', 0),
            'limits': limits
        }
    
    def record_trade(self, symbol: str, qty: int, price: float, trade_type: str) -> bool:
        """Record a trade for margin tracking (paper trading)."""
        if self._margin_checker and self.paper_trade:
            try:
                self._margin_checker.simulator.record_trade(symbol, qty, price, trade_type)
                self._margin_checker.simulator.save_state()
                return True
            except Exception as e:
                self.logger.error(f"[MARGIN] Error recording trade: {e}")
        return False
    
    def get_positions(self) -> list:
        """Get current positions (paper trading)."""
        if self._margin_checker and self.paper_trade:
            return self._margin_checker.simulator.get_positions()
        return []
    
    def clear_positions(self) -> bool:
        """Clear all positions (paper trading)."""
        if self._margin_checker and self.paper_trade:
            try:
                self._margin_checker.simulator.clear_positions()
                self._margin_checker.simulator.save_state()
                return True
            except Exception as e:
                self.logger.error(f"[MARGIN] Error clearing positions: {e}")
        return False
    
    def get_used_margin(self) -> float:
        """Get used margin amount."""
        if self._margin_checker:
            return self._margin_checker.simulator.used_margin()
        return 0
    
    def get_available_margin(self) -> float:
        """Get available margin amount."""
        if self._margin_checker:
            return self._margin_checker.simulator.available_margin()
        limits = self.get_limits()
        return limits.get('available', 0)
