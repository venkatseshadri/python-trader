import pandas as pd
import os
import glob

def analyze_latest_ledger():
    list_of_files = glob.glob('backtest_results/Orbitron_Trades_*.xlsx')
    if not list_of_files:
        print("❌ No trade ledger found.")
        return
    
    latest_file = max(list_of_files, key=os.path.getctime)
    print(f"📊 Analyzing Latest Ledger: {latest_file}")
    
    df = pd.read_excel(latest_file)
    
    # In Orbitron Excel:
    # 'amount' is the trade PnL
    # 'txn_type' identifies entry/exit (or similar)
    
    if df.empty:
        print("⚠️ Ledger is empty.")
        return

    # Total PnL is the sum of the 'amount' column
    total_pnl = df['amount'].sum()
    win_rate = (df['amount'] > 0).mean() * 100
    
    print("\n📈 OVERALL PERFORMANCE (Jan 2026):")
    print("-" * 50)
    print(f"Total P&L: Rs.{total_pnl:,.2f}")
    print(f"Win Rate:  {win_rate:.1f}%")
    print(f"Total Trades: {len(df)}")

    stock_stats = df.groupby('Instrument').agg({'amount': ['sum', 'count', 'mean']})
    print("\n🏢 PERFORMANCE BY STOCK:")
    print("-" * 50)
    print(stock_stats.to_string())

if __name__ == "__main__":
    analyze_latest_ledger()
