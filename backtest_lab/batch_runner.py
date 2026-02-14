import argparse
import sys
import os

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backtest_lab.core.loader import DataLoader
from backtest_lab.core.runner import ScenarioRunner

def main():
    parser = argparse.ArgumentParser(description='Orbiter Batch Runner')
    parser.add_argument('--csv', required=True, help='Path to NIFTY 50 archive CSV')
    parser.add_argument('--days', type=int, default=250, help='Days to backtest')
    args = parser.parse_args()

    # 1. Load Data
    loader = DataLoader(args.csv)
    full_df = loader.load_data()
    
    dates = full_df['date'].dt.date.unique()
    target_dates = dates[-args.days:]
    df = full_df[full_df['date'].dt.date.isin(target_dates)].copy()
    
    print(f"🔬 Batch testing {len(target_dates)} sessions...")

    # 2. Run all JSON scenarios
    scenario_dir = os.path.join(os.path.dirname(__file__), 'scenarios')
    runner = ScenarioRunner(loader, df)
    runner.run_all_from_folder(scenario_dir)

    # 3. Output Summary
    print("\n" + "="*70)
    print(f"🏆 BATCH BACKTEST SUMMARY (Last {args.days} Days)")
    print("="*70)
    print(runner.get_summary().to_string(index=False))

if __name__ == "__main__":
    main()
