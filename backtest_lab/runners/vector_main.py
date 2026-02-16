import argparse
import sys
import os
import time
import pandas as pd
import json

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from backtest_lab.core.mass_engine import MassOptimizer

def load_scenarios(scenario_dir):
    scenarios = []
    if not os.path.exists(scenario_dir): return []
    
    # Recursively find all JSONs in batches
    for root, dirs, files in os.walk(scenario_dir):
        for f in files:
            if f.endswith('.json'):
                with open(os.path.join(root, f)) as j:
                    try:
                        data = json.load(j)
                        scenarios.append({
                            'name': data.get('name', f),
                            'weights': data['config']['weights'],
                            'threshold': data['config']['trade_threshold']
                        })
                    except Exception as e:
                        print(f"⚠️ Skip {f}: {e}")
    return scenarios

def main():
    parser = argparse.ArgumentParser(description='Orbiter Full-Archive Vector Runner')
    parser.add_argument('--csv', required=True, help='Path to NIFTY 50 archive')
    parser.add_argument('--days', type=int, default=2500, help='Days to backtest (Full Archive)')
    args = parser.parse_args()

    # 1. Load the target scenarios
    scenario_dir = os.path.join(os.path.dirname(__file__), 'scenarios')
    scenarios = load_scenarios(scenario_dir)
    print(f"📂 Loaded {len(scenarios)} scenarios from {scenario_dir}")

    # 2. Setup Mass Engine (Full History)
    optimizer = MassOptimizer(args.csv)
    optimizer.precalculate_scores(days=args.days)

    # 3. Execute Vectorized Simulation
    print(f"\n🚀 Running Full Archive Simulation ({args.days} days) for all scenarios...")
    start_t = time.time()
    results = optimizer.run_grid_search(scenarios)
    end_t = time.time()

    # 4. Output Summary
    print("\n" + "="*70)
    print(f"🏆 FULL ARCHIVE PERFORMANCE LEADERBOARD ({args.days} Days)")
    print("="*70)
    if not results.empty:
        print(results.drop(columns=['Config']).to_string(index=False))
    else:
        print("⚠️ No results generated.")
    
    print(f"\n⚡ Total Execution Time: {end_t - start_t:.2f} seconds.")

if __name__ == "__main__":
    main()
