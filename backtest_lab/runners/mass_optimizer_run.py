import argparse
import sys
import os
import time
import pandas as pd
import json

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from backtest_lab.core.generator import ScenarioGenerator
from backtest_lab.core.mass_engine import MassOptimizer

def save_top_scenarios(results, output_dir, top_n=100):
    """Saves only the best-performing configurations to disk."""
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    print(f"💾 Saving Top {top_n} JSON files to {output_dir}...")
    
    top_list = results.head(top_n).to_dict('records')
    for i, res in enumerate(top_list):
        filename = f"top_{i+1:03d}_{res['Scenario']}.json"
        path = os.path.join(output_dir, filename)
        with open(path, 'w') as f:
            json.dump(res['Config'], f, indent=2)

def main():
    parser = argparse.ArgumentParser(description='Orbiter Mass Optimizer')
    parser.add_argument('--csv', required=True)
    parser.add_argument('--days', type=int, default=250)
    args = parser.parse_args()

    # 1. Generate the Grid (19,000+ scenarios in memory)
    print("🎨 Generating Universal Scenarios in memory...")
    gen = ScenarioGenerator()
    scenarios = gen.get_universal_scenarios()
    print(f"✅ Generated {len(scenarios)} combinations.")

    # 2. Setup Mass Engine & Pre-calculate
    optimizer = MassOptimizer(args.csv)
    optimizer.precalculate_scores(days=args.days)

    # 3. Execute Grid Search
    print("\n" + "="*20 + " RUNNING GRID SEARCH " + "="*20)
    start_t = time.time()
    results = optimizer.run_grid_search(scenarios)
    end_t = time.time()

    if results.empty:
        print("⚠️ No results found.")
        return

    # Sort by ROI% then PF
    results = results.sort_values(['ROI%', 'PF'], ascending=False)

    # 4. Save only Top 100 for audit
    json_dir = os.path.join(os.path.dirname(__file__), 'scenarios_best')
    save_top_scenarios(results, json_dir, top_n=100)

    # 5. Output Leaderboard
    print("\n" + "🏆"*5 + " TOP 20 CONFIGURATIONS " + "🏆"*5)
    print(results.head(20).drop(columns=['Config']).to_string(index=False))
    
    print(f"\n⚡ Total Time: {end_t - start_t:.2f} seconds for {len(scenarios)} simulations.")
    print(f"📁 Top scenarios saved in: {json_dir}")

if __name__ == "__main__":
    main()
