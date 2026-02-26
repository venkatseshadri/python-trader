# orbiter/core/engine/action/executor.py

import logging
from typing import Dict, Any
from orbiter.utils.constants_manager import ConstantsManager
from orbiter.utils.schema_manager import SchemaManager

from .executors.equity import EquityActionExecutor, EquitySimulationExecutor
from .executors.options import OptionActionExecutor, OptionSimulationExecutor
from .executors.futures import FutureActionExecutor, FutureSimulationExecutor

logger = logging.getLogger("ORBITER")

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
        
        # 1. Determine Mode
        is_live = params.get('execute', True)
        
        # 2. Determine Category (Explicit 'derivative' priority)
        derivative_type = params.get('derivative', '').lower()
        
        if derivative_type == 'option':
            is_option, is_future = True, False
        elif derivative_type == 'future':
            is_option, is_future = False, True
        else:
            # Fallback to implicit checks
            is_option = params.get('option') is not None
            is_future = params.get('future') is not None or 'FUT' in params.get('symbol', '').upper()
        
        # 3. Route
        try:
            if is_option:
                worker = self._option_live if is_live else self._option_sim
            elif is_future:
                worker = self._future_live if is_live else self._future_sim
            else:
                worker = self._equity_live if is_live else self._equity_sim
                
            return worker.execute(**params)
            
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
