# orbiter/core/engine/action/executor.py

import logging
import time
from typing import Dict, Any
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager

from .executors.equity import EquityActionExecutor, EquitySimulationExecutor
from .executors.options import OptionActionExecutor, OptionSimulationExecutor
from .executors.futures import FutureActionExecutor, FutureSimulationExecutor

logger = logging.getLogger("ORBITER")

def get_available_margin(client) -> float:
    """Fetch available margin from broker."""
    try:
        limits = client.api.get_limits()
        if limits and limits.get('stat') == 'Ok':
            return float(limits.get('cash', 0))
    except Exception as e:
        logger.warning(f"Could not fetch margin: {e}")
    return 0.0

def check_margin_for_trade(client, exchange: str, symbol: str, required_margin: float) -> tuple:
    """Check if enough margin available. Returns (allowed, available, required)."""
    if exchange.upper() != 'MCX':
        return True, 0, 0  # Skip for non-MCX
    
    if required_margin <= 0:
        return True, 0, 0
    
    available = get_available_margin(client)
    if available >= required_margin:
        return True, available, required_margin
    else:
        return False, available, required_margin

class ActionExecutor:
    """
    Facade Executor. 
    Routes generic action requests to specialized workers (Equity, Option, Future).
    """
    _frozen = False  # Class-level freeze flag
    
    def __init__(self, state):
        self.state = state
        self.constants = ConstantsManager.get_instance()
        
        # Initialize specialized workers
        self._equity_live = EquityActionExecutor(state)
        self._equity_sim  = EquitySimulationExecutor(state)
        self._option_live = OptionActionExecutor(state)
        self._option_sim  = OptionSimulationExecutor(state)
        self._future_live = FutureActionExecutor(state)
        self._future_sim  = FutureSimulationExecutor(state)

        # Deduplication: track recently placed orders (symbol + side -> timestamp)
        self._recent_orders: Dict[str, float] = {}
        self._order_ttl_seconds = 60  # Orders valid for 60 seconds

    @classmethod
    def set_frozen(cls, frozen: bool):
        """Set frozen state - blocks all real trades"""
        cls._frozen = frozen
        
    @classmethod
    def is_frozen(cls) -> bool:
        """Check if trading is frozen"""
        return cls._frozen
    
    def place_order(self, **params: Dict):
        """
        🚀 Generic Order Operation Router
        """
        # 0. Check if frozen - block real trades
        is_live = params.get('execute', True)
        if is_live and ActionExecutor._frozen:
            logger.warning("⛔ TRADE BLOCKED: System is frozen. Use /unfreeze to enable trading.")
            return {"stat": "Ok", "blocked": True, "reason": "frozen"}
        
        # 1. Deduplication: Check if order already placed recently
        symbol = params.get('symbol', '')
        side = params.get('side', 'B')
        order_key = f"{symbol}:{side}".upper()
        
        current_time = time.time()
        if order_key in self._recent_orders:
            last_time = self._recent_orders[order_key]
            if current_time - last_time < self._order_ttl_seconds:
                logger.info(f"⏭️ Order deduplicated: {order_key} (last {current_time - last_time:.1f}s ago)")
                return {"stat": "Ok", "deduplicated": True, "reason": "recent_order_exists"}
        
        logger.debug(f"🔔 Order NOT deduplicated: {order_key} (first time or TTL expired)")
        
        # 2. Check if symbol already in active positions
        tsym = params.get('tsym', params.get('symbol', ''))
        for pos_key, pos_data in self.state.active_positions.items():
            pos_tsym = pos_data.get('tsym', '')
            if tsym and pos_tsym and tsym.upper() in pos_tsym.upper():
                logger.info(f"⏭️ Order blocked: {tsym} already in active positions")
                return {"stat": "Ok", "blocked": True, "reason": "already_in_positions"}
        
        # 3. MARGIN CHECK for MCX
        exchange = params.get('exchange', '').upper()
        if is_live and exchange == 'MCX':
            from orbiter.config.mcx.config import get_mcx_margin
            symbol_for_margin = params.get('symbol', '')
            required_margin = get_mcx_margin(symbol_for_margin)
            if required_margin > 0:
                allowed, available, required = check_margin_for_trade(
                    self.state.client, exchange, symbol_for_margin, required_margin
                )
                if not allowed:
                    logger.warning(f"⛔ MARGIN BLOCK: Need ₹{required:,.0f} but only ₹{available:,.0f} available for {symbol_for_margin}")
                    return {"stat": "Ok", "blocked": True, "reason": "insufficient_margin", "available": available, "required": required}
                logger.info(f"✅ Margin OK: ₹{available:,.0f} available, ₹{required:,.0f} required for {symbol_for_margin}")
        
        # 3. Determine Mode
        is_live = params.get('execute', True)
        
        # 2. Determine Category (Explicit 'derivative' priority)
        derivative_type = params.get('derivative', '').lower()
        
        if derivative_type == 'option':
            is_option, is_future = True, False
        elif derivative_type == 'future':
            is_option, is_future = False, True
        else:
            # Fallback to implicit checks - support both 'option' and 'option_type' keys
            is_option = params.get('option') is not None or params.get('option_type') is not None
            is_future = params.get('future') is not None or 'FUT' in params.get('symbol', '').upper()
        
        # 3. Route
        try:
            if is_option:
                worker = self._option_live if is_live else self._option_sim
            elif is_future:
                worker = self._future_live if is_live else self._future_sim
            else:
                worker = self._equity_live if is_live else self._equity_sim
                
            result = worker.execute(**params)
            
            # Track successful order for deduplication
            if result and result.get('ok') or result and result.get('stat') == 'Ok':
                self._recent_orders[order_key] = current_time
                # Cleanup old entries periodically
                if len(self._recent_orders) > 100:
                    self._recent_orders = {k: v for k, v in self._recent_orders.items() 
                                         if current_time - v < self._order_ttl_seconds}
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Execution Routing Failed: {e}")
            return None

    def send_alert(self, **params: Dict):
        """Action: Sends an alert message via the configured notifier."""
        msg = params.get('message', '🔔 System Alert')
        logger.info(f"ALARM: {msg}")
        # Integration with telegram_notifier could go here
        return True

    def square_off_all(self, **params: Dict):
        """Action: Closes all open positions."""
        logger.info(f"🧹 Squaring off all positions. Reason: {params.get('reason', 'Generic')}")
        # Simplified: Loop through active positions and fire market orders
        for pos in self.state.active_positions:
            self.place_order(
                symbol=pos['symbol'], 
                side='S' if pos['qty'] > 0 else 'B', 
                qty=abs(pos['qty']),
                remark="SQUARE_OFF"
            )
