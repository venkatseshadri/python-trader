import pandas as pd
import numpy as np
import os
import json

class Reporter:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def generate_report(self, trades, equity_curve, daily_stats, filename='backtest_report.html'):
        if not trades:
            print("⚠️ No trades generated. Skip report.")
            return

        df_trades = pd.DataFrame(trades)
        df_daily = pd.DataFrame(daily_stats)
        
        # 1. Calculate Key Metrics
        total_pnl_rs = df_daily['pnl_rs'].sum()
        roi = (total_pnl_rs / 100000) * 100
        win_rate = (len(df_trades[df_trades['pnl'] > 0]) / len(df_trades)) * 100
        max_dd = max([e.get('drawdown_pct', 0) for e in equity_curve])

        # 2. Monthly Heatmap Data
        df_daily['date'] = pd.to_datetime(df_daily['date'])
        df_daily['year'] = df_daily['date'].dt.year
        df_daily['month'] = df_daily['date'].dt.month
        monthly_returns = df_daily.groupby(['year', 'month'])['pnl_rs'].sum().unstack(fill_value=0)
        
        # 3. Histogram Data
        bins = np.linspace(-100, 100, 21) # +/- 100 points
        hist, edges = np.histogram(df_trades['pnl'], bins=bins)
        hist_labels = [f"{int(edges[i])} to {int(edges[i+1])}" for i in range(len(edges)-1)]

        # 4. JSON for Charts
        equity_labels = [str(e['date']) for e in equity_curve if e['date']]
        equity_data = [float(e['equity']) for e in equity_curve if e['date']]
        dd_data = [float(e['drawdown_pct']) for e in equity_curve if e['date']]

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Orbiter | Performance Report</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; color: #333; margin: 0; padding: 40px; }}
                .container {{ max-width: 1100px; margin: auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.05); }}
                .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }}
                .stat-card {{ background: #fff; padding: 20px; border-radius: 10px; border: 1px solid #eef; text-align: center; }}
                .stat-card h3 {{ margin: 0; font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; }}
                .stat-card p {{ margin: 10px 0 0; font-size: 24px; font-weight: 700; }}
                .chart-container {{ margin: 40px 0; background: #fff; padding: 20px; border-radius: 10px; border: 1px solid #eee; height: 400px; }}
                .heatmap-table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 12px; }}
                .heatmap-table th, .heatmap-table td {{ border: 1px solid #eee; padding: 10px; text-align: center; }}
                .heatmap-table th {{ background: #f8f9fa; }}
                .pos {{ background: #e8f5e9; color: #2e7d32; }}
                .neg {{ background: #ffebee; color: #c62828; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 style="margin:0;">🚀 Strategy Intelligence Report</h1>
                <p style="color:#666;">Analysis Period: {df_daily['date'].min().date()} to {df_daily['date'].max().date()}</p>

                <div class="stats-grid">
                    <div class="stat-card"><h3>Profit/Loss</h3><p style="color:{'#27ae60' if total_pnl_rs > 0 else '#e74c3c'}">₹{total_pnl_rs:,.2f}</p></div>
                    <div class="stat-card"><h3>Return on Cap</h3><p>{roi:.2f}%</p></div>
                    <div class="stat-card"><h3>Win Rate</h3><p>{win_rate:.1f}%</p></div>
                    <div class="stat-card"><h3>Max Drawdown</h3><p style="color:#e74c3c;">{max_dd:.2f}%</p></div>
                </div>

                <div class="chart-container"><canvas id="equityChart"></canvas></div>
                
                <h2>Monthly Profit Breakdown (₹)</h2>
                <table class="heatmap-table">
                    <thead>
                        <tr><th>Year</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th></tr>
                    </thead>
                    <tbody>
        """

        for year, row in monthly_returns.iterrows():
            html += f"<tr><td><strong>{year}</strong></td>"
            for m in range(1, 13):
                val = row.get(m, 0)
                cls = "pos" if val > 0 else ("neg" if val < 0 else "")
                html += f'<td class="{cls}">{val:,.0f}</td>'
            html += "</tr>"

        html += f"""
                    </tbody>
                </table>

                <div class="chart-container" style="height:300px;"><canvas id="histChart"></canvas></div>

                <div class="chart-container"><canvas id="ddChart"></canvas></div>
            </div>

            <script>
                new Chart(document.getElementById('equityChart'), {{
                    type: 'line',
                    data: {{
                        labels: {json.dumps(equity_labels)},
                        datasets: [{{
                            label: 'Net Equity',
                            data: {json.dumps(equity_data)},
                            borderColor: '#3498db',
                            fill: true,
                            backgroundColor: 'rgba(52, 152, 219, 0.05)',
                            tension: 0.4
                        }}]
                    }},
                    options: {{ responsive: true, maintainAspectRatio: false }}
                }});

                new Chart(document.getElementById('histChart'), {{
                    type: 'bar',
                    data: {{
                        labels: {json.dumps(hist_labels)},
                        datasets: [{{
                            label: 'Trade Profit Distribution (Points)',
                            data: {json.dumps(hist.tolist())},
                            backgroundColor: '#2ecc71'
                        }}]
                    }},
                    options: {{ responsive: true, maintainAspectRatio: false }}
                }});

                new Chart(document.getElementById('ddChart'), {{
                    type: 'line',
                    data: {{
                        labels: {json.dumps(equity_labels)},
                        datasets: [{{
                            label: 'Drawdown %',
                            data: {json.dumps(dd_data)},
                            borderColor: '#e74c3c',
                            backgroundColor: 'rgba(231, 76, 60, 0.1)',
                            fill: true
                        }}]
                    }},
                    options: {{ responsive: true, maintainAspectRatio: false }}
                }});
            </script>
        </body>
        </html>
        """
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w') as f:
            f.write(html)
        print(f"✅ Enhanced report generated: {path}")
