# orbiter/core/broker/order_manager.py
"""
Order Manager - handles order book and order history for both paper and broker trading.
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime


class OrderManager:
    """Manages order book and order history for trading."""
    
    def __init__(self, project_root: str = None, segment_name: str = None, paper_trade: bool = False):
        self.project_root = project_root
        self.segment_name = segment_name
        self.paper_trade = paper_trade
        self._orders: List[Dict] = []
        self._positions: List[Dict] = []
        
        if paper_trade:
            self._load_paper_positions()
    
    def _load_paper_positions(self):
        """Load paper positions from disk."""
        if not self.project_root:
            return
        path = os.path.join(self.project_root, 'orbiter', 'data', 'paper_positions.json')
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                    # Handle both formats: {"positions": {...}} or {"positions": [...]} or direct [...]
                    if isinstance(data, dict):
                        pos_data = data.get('positions', {})
                        if isinstance(pos_data, dict):
                            # Dict format: {"positions": {"key": {...}, "key2": {...}}}
                            self._positions = list(pos_data.values()) if pos_data else []
                        elif isinstance(pos_data, list):
                            # List format: {"positions": [...]}
                            self._positions = pos_data
                        else:
                            self._positions = []
                    elif isinstance(data, list):
                        # Direct list format: [...]
                        self._positions = data
                    else:
                        self._positions = []
            except Exception as e:
                print(f"Error loading paper positions: {e}")
                self._positions = []
    
    def _save_paper_positions(self):
        """Save paper positions to disk."""
        if not self.project_root:
            return
        path = os.path.join(self.project_root, 'orbiter', 'data', 'paper_positions.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            with open(path, 'w') as f:
                json.dump(self._positions, f, indent=2)
        except:
            pass
    
    def record_order(self, order_result: Dict):
        """Record an order after execution."""
        if not order_result:
            return
        
        order = {
            'order_id': order_result.get('order_id') or order_result.get('norenordno') or f"PAPER_{len(self._orders)+1}",
            'symbol': order_result.get('tsym') or order_result.get('symbol'),
            'side': order_result.get('side'),
            'quantity': order_result.get('lot_size') or order_result.get('quantity'),
            'status': 'FILLED' if order_result.get('ok') else 'REJECTED',
            'timestamp': datetime.now().isoformat(),
            'paper_trade': self.paper_trade,
            'details': order_result
        }
        self._orders.append(order)
        
        # Update positions for paper trading
        if self.paper_trade and order_result.get('ok'):
            self._update_paper_position(order)
    
    def _update_paper_position(self, order: Dict):
        """Update paper position after order."""
        symbol = order['symbol']
        qty = order['quantity']
        side = order['side']
        
        # Find existing position
        for pos in self._positions:
            if pos.get('symbol') == symbol:
                if side == 'B':
                    pos['quantity'] = pos.get('quantity', 0) + qty
                else:
                    pos['quantity'] = pos.get('quantity', 0) - qty
                pos['updated'] = datetime.now().isoformat()
                break
        else:
            # New position
            self._positions.append({
                'symbol': symbol,
                'quantity': qty if side == 'B' else -qty,
                'created': datetime.now().isoformat()
            })
        
        self._save_paper_positions()
    
    def get_order_history(self) -> List[Dict]:
        """Get order history."""
        return self._orders
    
    def get_positions(self) -> List[Dict]:
        """Get current positions."""
        return [p for p in self._positions if p.get('quantity', 0) != 0]
    
    def get_total_pnl(self) -> float:
        """Calculate total P&L from paper positions."""
        # This would need price data to calculate properly
        return 0.0
    
    def clear_positions(self):
        """Clear all paper positions."""
        self._positions = []
        self._orders = []
        self._save_paper_positions()
