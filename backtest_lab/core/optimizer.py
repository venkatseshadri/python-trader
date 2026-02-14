import pandas as pd
from .engine import BacktestEngine

class ScenarioManager:
    def __init__(self, data_loader, full_df):
        self.loader = data_loader
        self.df = full_df
        self.results = []

    def run_scenario(self, name, config):
        """Runs a full simulation for a given config and returns metrics."""
        print(f"🧪 Running Scenario: {name}...")
        engine = BacktestEngine(self.loader, config)
        
        dates = self.df['date'].dt.date.unique()
        for d in dates:
            day_data = self.df[self.df['date'].dt.date == d].copy()
            engine.run_day(day_data)
            engine.finalize_day(d)

        # Summarize Results
        total_pnl = sum(t['pnl'] for t in engine.trades)
        wins = len([t for t in engine.trades if t['pnl'] > 0])
        win_rate = (wins / len(engine.trades) * 100) if engine.trades else 0
        
        res = {
            'Scenario': name,
            'Total PnL (Pts)': round(total_pnl, 2),
            'ROI %': round((total_pnl * 50 / 100000) * 100, 2),
            'Win Rate %': round(win_rate, 2),
            'Trades': len(engine.trades),
            'Max Drawdown %': round(engine.max_drawdown, 2)
        }
        self.results.append(res)
        return res

    def get_summary(self):
        return pd.DataFrame(self.results)
