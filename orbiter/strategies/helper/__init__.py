from .base import OrbiterState
from .evaluator import Evaluator
from .executor import Executor
from .syncer import Syncer

class OrbiterHelper:
    def __init__(self, client, symbols, filters_module, config):
        self.state = OrbiterState(client, symbols, filters_module, config)
        self.evaluator = Evaluator()
        self.executor = Executor()
        self.syncer = Syncer()

    @property
    def symbols(self): return self.state.symbols
    
    @property
    def active_positions(self): return self.state.active_positions
    
    @property
    def last_scan_metrics(self): return self.state.last_scan_metrics

    def evaluate_filters(self, token):
        return self.evaluator.evaluate_filters(self.state, token)

    def evaluate_all(self):
        scores = {}
        self.state.last_scan_metrics = []
        for token in self.state.symbols:
            score = self.evaluate_filters(token)
            if score != 0: scores[token] = score
        return scores

    def rank_signals(self, scores):
        return self.executor.rank_signals(self.state, scores, self.syncer)

    def square_off_all(self, reason="EOD EXIT"):
        return self.executor.square_off_all(self.state, reason)

    def check_sl(self):
        return self.executor.check_sl(self.state, self.syncer)

    def sync_active_positions_to_sheets(self):
        self.syncer.sync_active_positions_to_sheets(self.state)

    def is_market_hours(self):
        from datetime import datetime
        import pytz
        now = datetime.now(pytz.timezone('Asia/Kolkata')).time()
        return (self.state.config['MARKET_OPEN'] <= now <= self.state.config['MARKET_CLOSE'])
