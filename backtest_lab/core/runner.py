import json
import os
import pandas as pd
from datetime import datetime
from .engine import BacktestEngine
from .analytics import StrategyAnalytics

class ScenarioRunner:
    def __init__(self, data_loader, full_df):
        self.loader = data_loader
        self.df = full_df
        self.results = []

    def run_all_from_folder(self, scenarios_dir):
        """Recursively scans folder for JSON files and runs each."""
        scenario_files = []
        for root, dirs, files in os.walk(scenarios_dir):
            for f in files:
                if f.endswith('.json'):
                    scenario_files.append(os.path.join(root, f))
        
        scenario_files.sort()
        print(f"📂 Found {len(scenario_files)} scenarios in {scenarios_dir}")
        
        dates = self.df['date'].dt.date.unique()
        
        for path in scenario_files:
            with open(path) as j:
                try:
                    data = json.load(j)
                    # Support both old and new JSON formats
                    config = data.get('config', data)
                    name = data.get('name', os.path.basename(path))
                    
                    print(f"🧪 Running: {name}...")
                    engine = BacktestEngine(self.loader, config)
                    
                    for d in dates:
                        day_data = self.df[self.df['date'].dt.date == d].copy()
                        engine.run_day(day_data)
                        engine.finalize_day(d)

                    # Advanced Metrics
                    metrics = StrategyAnalytics.calculate_metrics(engine.trades, engine.daily_stats)
                    total_pnl = sum(t['pnl'] for t in engine.trades)
                    
                    self.results.append({
                        'Scenario': name,
                        'ROI %': round((total_pnl * 50 / 100000) * 100, 2),
                        'Sharpe': metrics['sharpe'],
                        'PF': metrics['profit_factor'],
                        'Win%': metrics['win_rate'],
                        'Trades': len(engine.trades),
                        'MaxDD%': round(engine.max_drawdown, 2)
                    })
                except Exception as e:
                    print(f"⚠️ Failed to run scenario {path}: {e}")

    def get_summary(self):
        return pd.DataFrame(self.results)
