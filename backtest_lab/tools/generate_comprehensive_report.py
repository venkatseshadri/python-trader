import pandas as pd
import os

def generate_stock_deep_dive(csv_path, symbol, date, output_path):
    df = pd.read_csv(csv_path)
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    target_date = pd.to_datetime(date).date()
    row = df[(df['Symbol'] == symbol) & (df['Date'] == target_date)]
    if row.empty:
        row = df[df['Symbol'] == symbol].head(1)
        if row.empty: return
        date = row.iloc[0]['Date']
    data = row.iloc[0].to_dict()

    sections = {
        "1. Identity & Magnitude": ["Date", "Symbol", "Direction", "Total_Move%", "Prev_Close", "Day_High", "Day_Low"],
        "2. Structural Trend (1D)": ["EMA20_1D", "EMA50_1D", "EMA100_1D", "EMA20_Slope", "Trend_Bull_Proof", ("Trend_Aligned", "Trend_Proof")],
        "3. Opening & Daily Conditions": ["Open_gt_YClose", "LTP_gt_YHigh", "Low_lt_YHigh", "Gap%", ("Weekly_Color", "Weekly_Proof")],
        "4. Short-Term Dynamics (1M)": ["EMA_5_9_Crosses", "EMA5_gt_9_Always", "Ribbon_Compressed", "Short_Term_Proof"],
        "5. Swings & Pullback Logic": ["Swing_High", "Swing_Low", "Trend_Move_Pts", "PB_Depth%", "PB_Time", "Is_Reversal", "PB_Proof"],
        "6. Multi-TF Wick Evidence (@ Trough)": ["Wick_1M_L", "Wick_5M_L", "Wick_15M_L", "Wick_1M_U", "Wick_5M_U", "Wick_15M_U", "Wick_Proof"],
        "7. Exhaustion & Decay": ["Sideways_Post_Gap", "ATR_Compression", "ADX_Exhaustion", "PrePB_Small_Candles", "PrePeak_Wick_U"],
        "8. Timing Analysis": ["Best_Bucket", "B1_Move%", "B4_Move%", "Timing_Proof"]
    }

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Master Evidence Deep Dive: {symbol}</title>
        <style>
            body {{ font-family: -apple-system, system-ui, sans-serif; line-height: 1.5; color: #24292e; max-width: 1100px; margin: 0 auto; padding: 20px; background: #f6f8fa; }}
            h1 {{ border-bottom: 2px solid #eaecef; padding-bottom: 0.3em; color: #0366d6; }}
            .card {{ background: white; border: 1px solid #d1d5da; border-radius: 6px; padding: 15px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .sec {{ margin-bottom: 30px; background: white; border: 1px solid #d1d5da; border-radius: 6px; overflow: hidden; }}
            .sec-title {{ background: #24292e; color: white; padding: 10px 15px; font-weight: bold; font-size: 0.9em; text-transform: uppercase; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px 15px; border-bottom: 1px solid #e1e4e8; text-align: left; vertical-align: top; }}
            th {{ background: #f1f8ff; width: 30%; color: #0366d6; font-size: 0.8em; text-transform: uppercase; }}
            .val {{ font-weight: bold; font-family: monospace; }}
            .proof {{ font-size: 0.85em; color: #586069; background: #fcf8e3; padding: 4px 8px; border-radius: 3px; border: 1px solid #faebcc; margin-top: 5px; display: inline-block; }}
            .true {{ color: #28a745; }} .false {{ color: #d73a49; }}
            .neg {{ color: #d73a49; }} .pos {{ color: #28a745; }}
        </style>
    </head>
    <body>
        <h1>🛡️ Master Analysis Proof: {symbol} ({date})</h1>
        <div class="card">
            <strong>Target Direction:</strong> {data['Direction']} | <strong>Total Move:</strong> <span class="val {'pos' if data['Total_Move%'] > 0 else 'neg'}">{data['Total_Move%']}%</span>
        </div>
    """

    for name, props in sections.items():
        html += f'<div class="sec"><div class="sec-title">{name}</div><table>'
        for p in props:
            if isinstance(p, tuple):
                p_name, proof_name = p
                val = data.get(p_name, "N/A")
                proof = data.get(proof_name, "N/A")
                css = "true" if val is True else ("false" if val is False else "")
                html += f'<tr><th>{p_name.replace("_", " ")}</th><td><span class="val {css}">{val}</span><br/><div class="proof">🧾 {proof}</div></td></tr>'
            else:
                val = data.get(p, "N/A")
                is_proof = p.endswith("_Proof") or p.endswith("_Details")
                if is_proof:
                    html += f'<tr><th>{p.replace("_", " ")}</th><td><div class="proof">🧾 {val}</div></td></tr>'
                else:
                    css = "true" if val is True else ("false" if val is False else ("pos" if isinstance(val, (int, float)) and val > 0 else ("neg" if isinstance(val, (int, float)) and val < 0 else "")))
                    html += f'<tr><th>{p.replace("_", " ")}</th><td><span class="val {css}">{val}</span></td></tr>'
        html += '</table></div>'

    html += """<footer style="text-align:center; color:#6a737d; font-size:0.8em; margin-top:40px;">Final Augmented Reverse Engineering Engine | Orbiter Backtest Lab</footer></body></html>"""
    with open(output_path, 'w') as f: f.write(html)
    print(f"✅ Master Report generated: {output_path}")

if __name__ == "__main__":
    generate_stock_deep_dive("backtest_lab/orbiter_revamp_data.csv", "ABB", "2026-01-08", "backtest_lab/abb_full_master_proof.html")
