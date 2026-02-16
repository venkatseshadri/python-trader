import argparse
import sys
import os

# Ensure the root project and backtest_lab are in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backtest_lab.core.loader import DataLoader
from backtest_lab.core.engine import BacktestEngine
from backtest_lab.core.reporter import Reporter

def main():
    parser = argparse.ArgumentParser(description='Orbiter Backtest Lab')
    parser.add_argument('--csv', required=True, help='Path to NIFTY 50 archive CSV')
    parser.add_argument('--days', type=int, default=5, help='Number of recent days to test')
    parser.add_argument('--report', default='backtest_report.html', help='Filename for the output report')
    args = parser.parse_args()

    # 1. Load Data
    loader = DataLoader(args.csv)
    df = loader.load_data()
    dates = df['date'].dt.date.unique()
    target_dates = dates[-args.days:]
    
    print(f"🔬 Testing {len(target_dates)} sessions: {target_dates[0]} to {target_dates[-1]}")

    # 2. Run Simulation
    engine = BacktestEngine(loader)
    
    for d in target_dates:
        print(f"▶️ Simulating {d}...")
        day_data = df[df['date'].dt.date == d].copy()
        engine.run_day(day_data)
        engine.finalize_day(d)

    # 3. Report
    print(f"\n📊 Simulation Complete. {len(engine.trades)} trades executed.")
    report_dir = os.path.join(os.path.dirname(__file__), 'reports')
    reporter = Reporter(report_dir)
    reporter.generate_report(engine.trades, engine.equity_curve, engine.daily_stats, filename=args.report)

if __name__ == "__main__":
    main()
