#!/usr/bin/env python3
"""Script to modify broker/__init__.py to use MarginAwareExecutor"""

import os

file_path = '/home/trading_ceo/python-trader/orbiter/core/broker/__init__.py'

with open(file_path, 'r') as f:
    content = f.read()

# Replace the import line
old_import = 'from .executor import OrderExecutor'
new_code = '''# Import executor - use margin-aware if paper trade
import os
paper_trade = os.environ.get("ORBITER_PAPER_TRADE", "true").lower() == "true"
if paper_trade:
    try:
        from orbiter.utils.margin.margin_executor import MarginAwareExecutor
        ExecutorClass = MarginAwareExecutor
        print("[MARGIN] Using MarginAwareExecutor (paper trade mode)")
    except ImportError:
        from .executor import OrderExecutor
        ExecutorClass = OrderExecutor
else:
    from .executor import OrderExecutor
    ExecutorClass = OrderExecutor
# Original: from .executor import OrderExecutor'''

content = content.replace(old_import, new_code)

# Also replace the executor initialization to use ExecutorClass
content = content.replace(
    'self.executor = OrderExecutor(self.conn.api, self._init_logger(), execution_policy=policy)',
    'self.executor = ExecutorClass(self.conn.api, self._init_logger(), execution_policy=policy, paper_trade=paper_trade)'
)

with open(file_path, 'w') as f:
    f.write(content)

print('Modified broker/__init__.py')
