import pandas as pd
import numpy as np
import os

def calculate_advanced_stats(trades_df, capital=100000):
    if trades_df.empty: return {}
    
    # 1. High-Resolution Cleaning (Trade-Level, not Daily)
    # We only care about the sequence of equity changes
    p_df = trades_df[trades_df['Action'] == 'SQUARE-OFF'].copy()
    p_df['PnL'] = pd.to_numeric(p_df['PnL_Rs'], errors='coerce').fillna(0)
    p_df['Time'] = pd.to_datetime(p_df['Time'])
    p_df = p_df.sort_values('Time')
    
    # 2. Equity and Drawdown (Trade-by-Trade)
    # Start with capital at T=0
    equity_sequence = [capital] + (p_df['PnL'].cumsum() + capital).tolist()
    time_sequence = [p_df['Time'].iloc[0] - pd.Timedelta(minutes=1)] + p_df['Time'].tolist()
    
    res_df = pd.DataFrame({'Time': time_sequence, 'Equity': equity_sequence})
    res_df['PnL_Sum'] = res_df['Equity'] - capital
    res_df['Running_Max'] = res_df['Equity'].cummax()
    res_df['Drawdown_Rs'] = res_df['Equity'] - res_df['Running_Max']
    res_df['Drawdown_Pct'] = (res_df['Drawdown_Rs'] / res_df['Running_Max']) * 100
    
    # 3. Maximum Drawdown Period (Duration based)
    # A segment starts when equity falls below peak and ends when a NEW peak is reached
    is_underwater = res_df['Equity'] < res_df['Running_Max']
    underwater_segments = []
    if is_underwater.any():
        start_idx = None
        for i in range(len(is_underwater)):
            if is_underwater[i] and start_idx is None:
                start_idx = i - 1 # The peak index
            elif not is_underwater[i] and start_idx is not None:
                duration = (res_df.loc[i, 'Time'] - res_df.loc[start_idx, 'Time']).days
                underwater_segments.append((start_idx, i, duration))
                start_idx = None
        if start_idx is not None:
            duration = (res_df['Time'].iloc[-1] - res_df.loc[start_idx, 'Time']).days
            underwater_segments.append((start_idx, len(res_df)-1, duration))

    if underwater_segments:
        longest = max(underwater_segments, key=lambda x: x[2])
        idx_start, idx_end, duration_days = longest
        dd_start_time = res_df.loc[idx_start, 'Time']
        dd_end_time = res_df.loc[idx_end, 'Time']
    else:
        dd_start_time, dd_end_time, duration_days = res_df['Time'].iloc[0], res_df['Time'].iloc[0], 0

    # 4. Standard Daily Metrics (for tables)
    p_df['Date'] = p_df['Time'].dt.date
    daily_df = p_df.groupby('Date').agg({'PnL': 'sum', 'Action': 'count'}).rename(columns={'Action': 'Trades'})
    daily_df['Returns%'] = (daily_df['PnL'] / capital) * 100
    daily_df = daily_df.reset_index()
    daily_df['Date'] = pd.to_datetime(daily_df['Date'])
    
    win_days = daily_df[daily_df['PnL'] > 0]
    loss_days = daily_df[daily_df['PnL'] < 0]
    
    def get_max_streak(series):
        if not series.any(): return 0
        return (series != series.shift()).cumsum()[series].value_counts().max()

    ann_std = daily_df['Returns%'].std() * np.sqrt(252) if len(daily_df) > 1 else 0
    sharpe = (daily_df['Returns%'].mean() / daily_df['Returns%'].std() * np.sqrt(252)) if daily_df['Returns%'].std() != 0 else 0
    
    stats = {
        "1 Capital Required": f"Rs. {capital:,.2f}",
        "2 Total Trading Days": len(daily_df),
        "3 Win Days": len(win_days),
        "4 Loss Days": len(loss_days),
        "5 Max Winning Streak Days": int(get_max_streak(daily_df['PnL'] > 0)),
        "6 Max Losing Streak Days": int(get_max_streak(daily_df['PnL'] < 0)),
        "7 Win Rate": f"{(len(win_days)/len(daily_df)*100):.2f}%" if len(daily_df)>0 else "0%",
        "8 Avg Monthly Profit": f"Rs. {(p_df['PnL'].sum() / (max(len(daily_df),1)/21)):,.2f}",
        "9 Total Profit": f"Rs. {p_df['PnL'].sum():,.2f}",
        "10 Avg Monthly ROI": f"{(p_df['PnL'].sum()/capital*100)/(max(len(daily_df),1)/21):.2f}%",
        "11 Total ROI": f"{(p_df['PnL'].sum()/capital*100):.2f}%",
        "12 Standard Deviation (Annualised)": f"{ann_std:.2f}%",
        "13 Sharpe Ratio (Annualised)": f"{sharpe:.2f}",
        "14 Sortino Ratio (Annualised)": "N/A",
        "15 Max Profit in a Day": f"Rs. {daily_df['PnL'].max():,.2f}",
        "16 Max Loss in a Day": f"Rs. {daily_df['PnL'].min():,.2f}",
        "17 Avg Profit/Loss Daily": f"Rs. {daily_df['PnL'].mean():,.2f}",
        "18 Avg Profit on Profit Days": f"Rs. {win_days['PnL'].mean():,.2f}" if not win_days.empty else "0",
        "19 Avg Loss on Loss Days": f"Rs. {loss_days['PnL'].mean():,.2f}" if not loss_days.empty else "0",
        "20 Avg no. of trades (Buy + Sell) per trading day": f"{(daily_df['Trades'].mean()*2):.2f}",
        "21 Max Drawdown": f"Rs. {res_df['Drawdown_Rs'].min():,.2f}",
        "22 Max Drawdown %": f"{res_df['Drawdown_Pct'].min():.2f}%"
    }

    # Rolling Metrics
    daily_df['Rolling_Sharpe'] = daily_df['Returns%'].rolling(21).mean() / daily_df['Returns%'].rolling(21).std() * np.sqrt(252)
    daily_df['Rolling_Vol'] = daily_df['Returns%'].rolling(21).std() * np.sqrt(252)

    # Monthly Matrix
    daily_df['MonthNum'] = daily_df['Date'].dt.month
    daily_df['Year'] = daily_df['Date'].dt.year
    monthly_matrix = daily_df.pivot_table(index='Year', columns='MonthNum', values='Returns%', aggfunc='sum').reindex(columns=range(1, 13)).fillna(0)
    monthly_matrix.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    # Monthly Summary Table
    daily_df['MonthLabel'] = daily_df['Date'].dt.strftime('%b-%Y')
    monthly_summary = daily_df.groupby('MonthLabel').agg({'PnL': 'sum', 'Trades': 'sum'}).reindex(daily_df['MonthLabel'].unique())
    monthly_summary['PnL%'] = (monthly_summary['PnL'] / capital) * 100
    
    return {
        "Statistics": stats,
        "DOW": daily_df.groupby(daily_df['Date'].dt.day_name()).agg({'Returns%':'sum', 'PnL':['max','min']}).reindex(['Monday','Tuesday','Wednesday','Thursday','Friday']),
        "MonthlyTable": monthly_summary,
        "MonthlyMatrix": monthly_matrix,
        "RawDaily": daily_df,
        "RawEquity": res_df,
        "DD_Meta": (dd_start_time, dd_end_time, duration_days)
    }
