import pandas as pd
import numpy as np

class StrategyAnalytics:
    @staticmethod
    def calculate_metrics(trades, daily_stats, initial_capital=100000):
        if not trades:
            return {"sharpe": 0, "profit_factor": 0, "win_rate": 0}
        
        df_trades = pd.DataFrame(trades)
        df_daily = pd.DataFrame(daily_stats)
        
        # 1. Profit Factor (Gross Wins / Gross Losses)
        wins = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
        losses = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
        profit_factor = wins / losses if losses > 0 else (wins if wins > 0 else 0)
        
        # 2. Sharpe Ratio (Daily returns base)
        # Assuming risk-free rate is 0 for simplicity in backtests
        daily_returns = df_daily['pnl_rs'] / initial_capital
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
        else:
            sharpe = 0
            
        win_rate = (len(df_trades[df_trades['pnl'] > 0]) / len(df_trades)) * 100
        
        return {
            "sharpe": round(sharpe, 2),
            "profit_factor": round(profit_factor, 2),
            "win_rate": round(win_rate, 2)
        }

    @staticmethod
    def analyze_days_of_week(daily_stats):
        """Calculates profitability grouped by day name (Monday-Friday)."""
        df = pd.DataFrame(daily_stats)
        if df.empty: return "No Data"
        
        # Aggregate
        summary = df.groupby('day_name')['pnl_rs'].agg(['sum', 'mean', 'count']).rename(
            columns={'sum': 'Total Profit (₹)', 'mean': 'Avg Profit/Day (₹)', 'count': 'Trading Days'}
        )
        # Order by conventional week
        order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        summary = summary.reindex(order)
        return summary

    @staticmethod
    def find_best_hours(trades):
        """Analyzes trade success based on entry hour."""
        if not trades: return "No Data"
        df = pd.DataFrame(trades)
        df['hour'] = df['entry_time'].dt.hour
        return df.groupby('hour')['pnl'].sum().sort_values(ascending=False)
