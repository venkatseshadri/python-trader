import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from fpdf import FPDF
from datetime import datetime
import seaborn as sns
import matplotlib.dates as mdates

class OrbitronPDF(FPDF):
    def header(self):
        # Brand Header
        self.set_font('Arial', 'B', 28)
        self.set_text_color(44, 62, 80)
        self.cell(100, 15, 'ORBITRON', 0, 0, 'L')
        
        self.set_font('Arial', 'B', 16)
        self.set_xy(140, 10)
        self.set_text_color(0, 0, 0)
        self.cell(60, 10, 'Backtest Report', 0, 1, 'R')
        
        self.set_font('Arial', '', 9)
        self.set_xy(140, 18)
        self.cell(60, 5, f'Created On  : {datetime.now().strftime("%b %d %Y")}', 0, 1, 'R')
        self.set_xy(140, 23)
        self.cell(60, 5, f'Generated In : 1 minutes', 0, 1, 'R')
        
        self.set_draw_color(52, 152, 219)
        self.line(10, 35, 200, 35)
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'B', 12)
        self.set_text_color(231, 76, 60)
        self.cell(190, 10, str(self.page_no()), 0, 0, 'R')

def generate_pro_charts(equity_df, daily_df, dd_meta, output_dir, capital=100000):
    charts = {}
    sns.set_style("whitegrid")
    
    # 1. PNL Curve (Shaded)
    plt.figure(figsize=(10, 4))
    pnl_sum = daily_df['PnL'].cumsum()
    plt.plot(daily_df['Date'], pnl_sum, color='#4a90e2', linewidth=1.5)
    plt.fill_between(daily_df['Date'], 0, pnl_sum, color='#4a90e2', alpha=0.2)
    plt.title('PNL curve', fontweight='bold', color='#e67e22', loc='left', fontsize=16)
    plt.ylabel('Total PNL')
    plt.grid(True, alpha=0.2)
    p1 = os.path.join(output_dir, 'c_pnl.png')
    plt.savefig(p1, bbox_inches='tight', dpi=150)
    charts['equity'] = p1
    plt.close()

    # 2. Drawdown Plot
    plt.figure(figsize=(10, 4))
    equity = pnl_sum + capital
    running_max = equity.cummax()
    dd = (equity - running_max) / running_max * 100
    plt.fill_between(daily_df['Date'], dd, 0, color='#3498db', alpha=0.3)
    plt.plot(daily_df['Date'], dd, color='#2980b9', linewidth=1)
    plt.axvspan(dd_meta[0], dd_meta[1], color='#f06292', alpha=0.3)
    plt.title('Drawdown plot', fontweight='bold', color='#e67e22', loc='left', fontsize=16)
    plt.ylabel('% of last peak')
    plt.grid(True, alpha=0.2)
    p2 = os.path.join(output_dir, 'c_dd.png')
    plt.savefig(p2, bbox_inches='tight', dpi=150)
    charts['drawdown'] = p2
    plt.close()

    # 3. Rolling Metrics
    plt.figure(figsize=(10, 4))
    plt.subplot(2, 1, 1)
    plt.plot(daily_df['Date'], daily_df['Rolling_Sharpe'], color='#2980b9', label='Sharpe ratio')
    plt.title('Rolling metrics', fontweight='bold', color='#e67e22', loc='left', fontsize=14)
    plt.legend()
    plt.subplot(2, 1, 2)
    plt.plot(daily_df['Date'], daily_df['Rolling_Vol'], color='#4a90e2', label='Volatility %')
    plt.legend()
    p3 = os.path.join(output_dir, 'c_rolling.png')
    plt.savefig(p3, bbox_inches='tight', dpi=150)
    charts['rolling'] = p3
    plt.close()

    # 4. Returns Histogram
    plt.figure(figsize=(10, 4))
    valid_returns = daily_df[daily_df['PnL'] != 0]['Returns%']
    if not valid_returns.empty:
        # Improved histogram: more bins, clear edges, and alpha
        sns.histplot(valid_returns, kde=True, color='#1abc9c', bins=30, alpha=0.6, edgecolor='white')
        plt.axvline(0, color='red', linestyle='--', alpha=0.5)
    plt.title('Returns histogram', fontweight='bold', color='#e67e22', loc='left', fontsize=16)
    plt.xlabel('Daily Returns %')
    p4 = os.path.join(output_dir, 'c_hist.png')
    plt.savefig(p4, bbox_inches='tight', dpi=150)
    charts['hist'] = p4
    plt.close()

    # 5. Daily Returns Bar
    plt.figure(figsize=(10, 4))
    colors = ['#2ecc71' if x > 0 else '#e74c3c' for x in daily_df['Returns%']]
    plt.bar(daily_df['Date'], daily_df['Returns%'], color=colors)
    plt.title('Daily returns', fontweight='bold', color='#e67e22', loc='left', fontsize=16)
    p5 = os.path.join(output_dir, 'c_daily.png')
    plt.savefig(p5, bbox_inches='tight', dpi=150)
    charts['daily_bars'] = p5
    plt.close()

    return charts

def generate_calendar_charts(daily_df, output_dir):
    years = daily_df['Date'].dt.year.unique()
    calendar_files = {}
    for year in years:
        df_year = daily_df[daily_df['Date'].dt.year == year]
        fig, axes = plt.subplots(3, 4, figsize=(15, 10))
        fig.suptitle(f"{year} Daily returns", fontsize=20, fontweight='bold', color='#e67e22', y=0.95)
        for month in range(1, 13):
            ax = axes[(month-1)//4, (month-1)%4]
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year+1, 1, 1)
            else:
                end = datetime(year, month+1, 1)
            month_range = pd.date_range(start, end, freq='D')[:-1]
            month_df = pd.DataFrame({'Date': month_range}).merge(df_year, on='Date', how='left').fillna(0)
            start_weekday = (start.weekday() + 0) % 7
            labels = [""] * 42
            colors = ["white"] * 42
            for i, row in month_df.iterrows():
                idx = i + start_weekday
                if idx >= 42: break
                val = row['Returns%']
                labels[idx] = f"{row['Date'].day}\n{val:.1f}%" if val != 0 else str(row['Date'].day)
                colors[idx] = "#2ecc71" if val > 0 else ("#e74c3c" if val < 0 else "#f9f9f9")
            
            ax.set_xlim(0, 7)
            ax.set_ylim(0, 6)
            ax.set_aspect('equal')
            ax.invert_yaxis()
            ax.set_xticks([])
            ax.set_yticks([])
            for y in range(6):
                for x in range(7):
                    idx = y * 7 + x
                    rect = plt.Rectangle((x, y), 1, 1, facecolor=colors[idx], edgecolor='white', lw=0.5)
                    ax.add_patch(rect)
                    ax.text(x+0.5, y+0.5, labels[idx], ha='center', va='center', fontsize=6)
            ax.set_title(start.strftime('%B'), fontsize=12, fontweight='bold')
        plt.tight_layout(rect=[0, 0.03, 1, 0.95])
        p = os.path.join(output_dir, f'cal_{year}.png')
        plt.savefig(p, dpi=120)
        calendar_files[year] = p
        plt.close()
    return calendar_files

def create_orbitron_report(data_dict, output_path, strategy_meta=None):
    pdf = OrbitronPDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    output_dir = os.path.dirname(output_path)
    
    # Use provided capital or default to 100,000
    capital = data_dict.get('Capital', 100000)
    
    charts = generate_pro_charts(data_dict['RawEquity'], data_dict['RawDaily'], data_dict['DD_Meta'], output_dir, capital=capital)
    
    # PAGE 1
    pdf.add_page()
    pdf.set_font('Arial', 'B', 9)
    
    # Default Meta if none provided
    if not strategy_meta:
        strategy_meta = {
            "Backtest ID": "3063922240623",
            "Strategy": "Institutional Sniper (Hybrid Multi-TF)",
            "Link": "https://github.com/vseshadri/python-trader/strategy/sniper",
            "Period": f"{data_dict['RawDaily']['Date'].min().strftime('%B %d, %Y')} to {data_dict['RawDaily']['Date'].max().strftime('%B %d, %Y')}",
            "Frequency": "1 Minute | Trade Price: Close | Type: positional",
            "Notes": "High Conviction 15m Entry with 1m Emergency SL and 70% Profit Retention."
        }

    for label, val in strategy_meta.items():
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(30, 5, f"{label}:", 0, 0)
        pdf.set_font('Arial', '', 9)
        if label == "Link": pdf.set_text_color(52, 152, 219)
        pdf.cell(0, 5, str(val), 0, 1)
        pdf.set_text_color(0, 0, 0)
    
    pdf.ln(2)
    pdf.image(charts['equity'], x=10, w=190)
    pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 4, "The PNL Curve x-axis represents time, while the y-axis represents the total PNL. The PNL curve starts at 0 and follows the ups and downs of the total PNL as it grows or declines over time.")
    pdf.ln(4)
    pdf.image(charts['drawdown'], x=10, w=190)
    start_date, end_date, duration = data_dict['DD_Meta']
    desc_dd = f"The drawdown plot represents a drop in PNL from the previous peak ( capital + PNL ). The x-axis represents time, while the y-axis represents the percentage of the peak. The vertical shaded pink region marks the maximum drawdown period (max number of days required to recover from a drawdown). In this case, the maximum drawdown period covers from {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}, a total of {duration} days."
    pdf.multi_cell(0, 4, desc_dd)

    # PAGE 2: Statistics & Daily Summary (Integrated)
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(231, 76, 60)
    pdf.cell(0, 10, 'Statistics', 0, 1, 'L')
    pdf.set_text_color(0, 0, 0)
    
    pdf.set_font('Arial', '', 8) 
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(15, 6, 'No', 1, 0, 'C', True)
    pdf.cell(100, 6, 'Name', 1, 0, 'L', True)
    pdf.cell(75, 6, 'Value', 1, 1, 'R', True)
    
    for i, (k, v) in enumerate(data_dict['Statistics'].items(), 1):
        pdf.cell(15, 5.5, str(i), 1, 0, 'C')
        # Handle key names that might not have a space-prefix number
        name = k.split(" ", 1)[1] if " " in k else k
        pdf.cell(100, 5.5, name, 1, 0, 'L')
        pdf.cell(75, 5.5, str(v), 1, 1, 'R')
        
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(231, 76, 60)
    pdf.cell(0, 10, 'Daily Summary', 0, 1, 'L')
    pdf.set_text_color(0, 0, 0)
    
    pdf.set_font('Arial', '', 8)
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(40, 6, 'Day', 1, 0, 'L', True)
    pdf.cell(50, 6, 'Returns (%)', 1, 0, 'R', True)
    pdf.cell(50, 6, 'Max profit (%)', 1, 0, 'R', True)
    pdf.cell(50, 6, 'Max loss (%)', 1, 1, 'R', True)
    
    dow_df = data_dict['DOW']
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']:
        if day in dow_df.index:
            row = dow_df.loc[day]
            pdf.cell(40, 5.5, day, 1, 0, 'L')
            pdf.cell(50, 5.5, f"{row[('Returns%', 'sum')]:.2f}", 1, 0, 'R')
            pdf.cell(50, 5.5, f"{(row[('PnL', 'max')]/capital*100):.2f}", 1, 0, 'R') 
            pdf.cell(50, 5.5, f"{(row[('PnL', 'min')]/capital*100):.2f}", 1, 1, 'R')

    # PAGE 3: Month Wise PNL Table
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(231, 76, 60)
    pdf.cell(0, 10, 'Month Wise PNL', 0, 1, 'L')
    pdf.set_text_color(0, 0, 0)
    
    pdf.set_font('Arial', '', 9)
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(50, 8, 'Month', 1, 0, 'L', True)
    pdf.cell(45, 8, 'Total Trades', 1, 0, 'R', True)
    pdf.cell(45, 8, 'PNL (Rs.)', 1, 0, 'R', True)
    pdf.cell(50, 8, 'PNL%', 1, 1, 'R', True)
    
    for month, row in data_dict['MonthlyTable'].iterrows():
        pdf.cell(50, 7, month, 1, 0, 'L')
        pdf.cell(45, 7, str(int(row['Trades'])), 1, 0, 'R')
        pdf.cell(45, 7, f"{row['PnL']/1000:.1f}K", 1, 0, 'R')
        pdf.cell(50, 7, f"{row['PnL%']:.2f}", 1, 1, 'R')

    # PAGE 4: Visual Analytics
    pdf.add_page()
    pdf.image(charts['hist'], x=10, w=190)
    pdf.ln(1)
    pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 4, "The Histogram of returns is a representation of the frequency distribution of daily PNL %. The x-axis represents daily PNL % while the y-axis represents the count of days in which that PNL% was achieved. The blue curve represents the Kernel density function (KDE). The histogram provides insight into the distribution of returns for the investment and can help identify the most common return ranges")
    
    pdf.ln(6)
    pdf.image(charts['daily_bars'], x=10, w=190)
    pdf.ln(1)
    pdf.multi_cell(0, 4, "The Daily Returns displays the daily returns on the y-axis and the dates on the x-axis. Each bar in the plot represents the return for a single day.")

    # PAGE 5: Rolling & Heatmap
    pdf.add_page()
    pdf.image(charts['rolling'], x=10, w=190)
    pdf.ln(1)
    pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 4, "This shows the Sharpe ratio and the volatility of the PNL Curve. The Sharpe ratio is a measure of the investment's return in excess of the risk-free rate (0%) per unit of volatility for a moving window of 21 days. A rising Sharpe ratio indicates an improvement in the risk-adjusted performance of the investment. A declining volatility over time suggests that the investment has become less risky.")
    
    pdf.ln(8)
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(231, 76, 60)
    pdf.cell(0, 10, 'Monthly returns', 0, 1, 'L')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', '', 9)
    pdf.multi_cell(0, 4, "The Monthly Returns Calendar displays the PNL % for each month along with total number of trades taken in the month.")
    
    pdf.ln(5)
    months_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font('Arial', 'B', 8)
    pdf.cell(20, 8, 'Year', 1, 0, 'C', True)
    for m in months_labels: pdf.cell(14.5, 8, m, 1, 0, 'C', True)
    pdf.ln(8)
    
    pdf.set_font('Arial', '', 8)
    matrix = data_dict['MonthlyMatrix']
    for year, row in matrix.iterrows():
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(20, 10, str(year), 1, 0, 'C', True)
        for val in row:
            if val > 0: pdf.set_fill_color(46, 204, 113)
            elif val < 0: pdf.set_fill_color(231, 76, 60)
            else: pdf.set_fill_color(255, 255, 255)
            txt = f"{val:.1f}%" if val != 0 else ""
            pdf.cell(14.5, 10, txt, 1, 0, 'C', True)
        pdf.ln(10)

    # PAGE 6+: Yearly Daily Calendars
    calendar_charts = generate_calendar_charts(data_dict['RawDaily'], output_dir)
    for year in sorted(calendar_charts.keys()):
        pdf.add_page()
        pdf.image(calendar_charts[year], x=5, w=200)
        pdf.ln(5)
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 4, "The Daily Returns Calendar displays the PNL % for each day.")

    for c in list(charts.values()) + list(calendar_charts.values()):
        if os.path.exists(c): os.remove(c)
    pdf.output(output_path)
    print(f"🚀 ORBITRON High-Fidelity Report Generated: {output_path}")
