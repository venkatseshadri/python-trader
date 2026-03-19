#!/usr/bin/env python3
"""Fix broker/__init__.py indentation issue"""

file_path = '/home/trading_ceo/python-trader/orbiter/core/broker/__init__.py'

with open(file_path, 'r') as f:
    content = f.read()

# Fix the broken executor initialization
old_block = """        # Only pass paper_trade when using MarginAwareExecutor
if paper_trade:
    self.executor = ExecutorClass(self.conn.api, self._init_logger(), execution_policy=policy, paper_trade=paper_trade)
else:
    self.executor = ExecutorClass(self.conn.api, self._init_logger(), execution_policy=policy)
        logger.debug(f"[{self.__class__.__name__}.__init__}] - Resolver, Margin, Executor (with policy) initialized."""

new_block = """        # Only pass paper_trade when using MarginAwareExecutor
        if paper_trade:
            self.executor = ExecutorClass(self.conn.api, self._init_logger(), execution_policy=policy, paper_trade=paper_trade)
        else:
            self.executor = ExecutorClass(self.conn.api, self._init_logger(), execution_policy=policy)
        logger.debug(f"[{self.__class__.__name__}.__init__}] - Resolver, Margin, Executor (with policy) initialized."""

content = content.replace(old_block, new_block)

with open(file_path, 'w') as f:
    f.write(content)

print('Fixed indentation')
