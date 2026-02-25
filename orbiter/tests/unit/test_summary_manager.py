import unittest
from types import SimpleNamespace

from orbiter.core.analytics.summary import SummaryManager, TaxCalculator


class FakeAPI:
    def __init__(self, quotes=None):
        self.quotes = quotes or {}

    def get_quotes(self, exchange=None, token=None):
        return self.quotes.get(str(token))


class FakeBroker:
    def __init__(self):
        self.api = FakeAPI({
            'RECLTD': {'lp': '612.5', 'c': '600'},
            'SPOT': {'lp': '610', 'c': '600'}
        })
        self._limits = {
            'available': 50000.0,
            'margin_used': 10000.0,
            'liquid_cash': 4000.0,
            'collateral_value': 10000.0,
            'total_power': 60000.0,
            'payin': 0.0
        }
        self._positions = [
            {'tsym': 'RECLTD', 'netqty': '25', 'rpnl': '200', 'urpnl': '50'}
        ]
        self._orders = [
            {'status': 'COMPLETE'},
            {'status': 'CANCELLED'}
        ]
        self._ltp = {'NSE|RECLTD': 612.5}
        self._option_ltp = {'ATM': 110.0, 'HEDGE': 20.0}

    def get_limits(self):
        return self._limits

    def get_positions(self):
        return self._positions

    def get_order_history(self):
        return self._orders

    def get_ltp(self, key):
        return self._ltp.get(key)

    def get_option_ltp_by_symbol(self, tsym):
        return self._option_ltp.get(tsym)

    def get_symbol(self, token, exchange='NSE'):
        return 'RECLTD'

    def get_token(self, symbol):
        return 'SPOT'


class FakeClient:
    def __init__(self):
        self.SYMBOLDICT = {
            'NSE|RECLTD': {'symbol': 'RECLTD', 'lp': 612.5, 'c': 600, 'o': 595}
        }

    def get_ltp(self, token):
        return 612.5

    def get_option_ltp_by_symbol(self, tsym):
        if tsym == 'ATM':
            return 110.0
        if tsym == 'HEDGE':
            return 20.0
        return None


class TestSummaryManager(unittest.TestCase):
    def test_tax_calculator(self):
        charges = TaxCalculator.estimate_charges(4, 10000, 'NFO')
        self.assertGreater(charges, 0)

    def test_generate_pre_session_report(self):
        broker = FakeBroker()
        sm = SummaryManager(broker, 'nfo', version='3.0')

        report = sm.generate_pre_session_report()
        self.assertIn('SESSION PREP', report)
        self.assertIn('Overnight Positions', report)
        self.assertIn('Warning', report)

    def test_generate_margin_status(self):
        broker = FakeBroker()
        sm = SummaryManager(broker, 'nfo', version='3.0')

        report = sm.generate_margin_status()
        self.assertIn('Margin Update', report)
        self.assertIn('Available', report)

    def test_generate_pnl_report(self):
        broker = FakeBroker()
        sm = SummaryManager(broker, 'nfo', version='3.0')

        state = SimpleNamespace(
            config={'SIMULATION': True},
            active_positions={
                'NSE|RECLTD': {
                    'symbol': 'RECLTD',
                    'entry_price': 600.0,
                    'strategy': 'FUTURE_LONG',
                    'lot_size': 25
                },
                'SPREAD': {
                    'symbol': 'RECLTD-SPREAD',
                    'entry_price': 0.0,
                    'strategy': 'SPREAD',
                    'atm_symbol': 'ATM',
                    'hedge_symbol': 'HEDGE',
                    'entry_net_premium': 100.0,
                    'lot_size': 25
                }
            },
            realized_pnl='500.0',
            trade_count='2'
        )

        report = sm.generate_pnl_report(state)
        self.assertIn('Total Day PnL', report)
        self.assertIn('Active Positions', report)

    def test_generate_live_scan_report(self):
        broker = FakeBroker()
        sm = SummaryManager(broker, 'nfo', version='3.0')

        state = SimpleNamespace(
            config={'SIMULATION': True},
            symbols=['NSE|RECLTD'],
            filter_results_cache={
                'NSE|RECLTD': {'f1': {'score': 1.5}},
                'NSE|OTHER': {'f1': {'score': -2.0}}
            },
            client=FakeClient(),
            active_positions={}
        )

        report = sm.generate_live_scan_report(state)
        self.assertIn('LIVE STATUS', report)
        self.assertIn('Top 10 Scans', report)
        self.assertIn('No active positions', report)

    def test_generate_post_session_report_sim(self):
        broker = FakeBroker()
        sm = SummaryManager(broker, 'nfo', version='3.0')

        state = SimpleNamespace(
            config={'SIMULATION': True},
            active_positions={
                'NSE|RECLTD': {
                    'symbol': 'RECLTD',
                    'entry_price': 600.0,
                    'strategy': 'FUTURE_LONG',
                    'lot_size': 25,
                    'pnl_rs': 250.0
                }
            },
            realized_pnl=500.0,
            trade_count=1
        )

        report = sm.generate_post_session_report(state)
        self.assertIn('SESSION DEBRIEF', report)
        self.assertIn('Net PnL', report)
        self.assertIn('T+1 Est. Margin', report)


if __name__ == '__main__':
    unittest.main()
