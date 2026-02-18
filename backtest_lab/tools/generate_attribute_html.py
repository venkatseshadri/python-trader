import pandas as pd
import os

def generate_html(csv_path, output_path):
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    
    # Sort by Date (newest first) and Symbol
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(['Date', 'Symbol'], ascending=[False, True])
    df['Date'] = df['Date'].dt.date

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>NIFTY Movers - Attribute Analysis</title>
        <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.5; color: #24292e; padding: 20px; background-color: #f6f8fa; }}
            h1 {{ border-bottom: 2px solid #eaecef; padding-bottom: 0.3em; color: #0366d6; }}
            .container {{ background: #fff; border: 1px solid #d1d5da; border-radius: 6px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            table.dataTable {{ font-size: 0.85em; border-collapse: collapse !important; }}
            th {{ background-color: #f1f8ff !important; color: #0366d6 !important; font-weight: 600; text-transform: uppercase; }}
            .neg {{ color: #d73a49; font-weight: bold; }}
            .pos {{ color: #28a745; font-weight: bold; }}
            .bool-true {{ color: #28a745; font-weight: bold; }}
            .bool-false {{ color: #d73a49; opacity: 0.6; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛡️ NIFTY 1% Movers - Comprehensive Attribute Analysis</h1>
            <p>Analyzing the last 50 trading days. Includes Intraday Extremes, EMA Dynamics, and Exhaustion Signals.</p>
            <table id="moversTable" class="display" style="width:100%">
                <thead>
                    <tr>
                        {headers}
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>

        <script src="https://code.jquery.com/jquery-3.7.0.js"></script>
        <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
        <script>
            $(document).ready(function() {{
                $('#moversTable').DataTable({{
                    "pageLength": 50,
                    "order": [[0, "desc"]],
                    "scrollX": true
                }});
            }});
        </script>
    </body>
    </html>
    """

    headers = "".join([f"<th>{col}</th>" for col in df.columns])
    
    rows = []
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            val = row[col]
            css_class = ""
            
            # Formatting logic
            if isinstance(val, (int, float)):
                if val < 0: css_class = "neg"
                elif val > 0: css_class = "pos"
            elif isinstance(val, bool):
                css_class = "bool-true" if val else "bool-false"
            
            cells.append(f"<td class='{css_class}'>{val}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")

    final_html = html_template.format(headers=headers, rows="".join(rows))
    
    with open(output_path, 'w') as f:
        f.write(final_html)
    
    print(f"✅ HTML Report generated: {output_path}")

if __name__ == "__main__":
    generate_html("backtest_lab/orbiter_revamp_data.csv", "backtest_lab/attribute_analysis.html")
