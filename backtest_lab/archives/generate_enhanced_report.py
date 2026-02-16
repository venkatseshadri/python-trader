import pandas as pd
import numpy as np
import talib
import os
import sys
from datetime import datetime, time as dt_time

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from backtest_lab.core.loader import DataLoader

# LOT SIZES
LOT_SIZES = {"RELIANCE": 250, "TCS": 175, "LT": 175, "SBIN": 750, "HDFCBANK": 550, "INFY": 400, "ICICIBANK": 700, "AXISBANK": 625, "BHARTIARTL": 475, "KOTAKBANK": 400}

class EnhancedPortfolioEngine:
    def __init__(self, top_n=5, threshold=0.35):
        self.top_n = top_n
        self.threshold = threshold
        self.active_positions = {} 
        self.all_trades = []
        self.weights = [1.0, 0.0, 1.5, 1.0, 0.0, 0.0, 0.0, 1.5]

    def run_simulation(self, stock_data_dict):
        # We assume data is already filtered for the target day
        stock_names = list(stock_data_dict.keys())
        max_len = max(len(df) for df in stock_data_dict.values())
        
        # Determine ORB for the day
        orb_levels = {}
        for name in stock_names:
            df_day = stock_data_dict[name]
            mask = (df_day['date'].dt.time >= dt_time(9, 15)) & (df_day['date'].dt.time <= dt_time(10, 0))
            if not df_day.empty and mask.any():
                orb_levels[name] = {'h': df_day.loc[mask, 'high'].max(), 'l': df_day.loc[mask, 'low'].min()}
            else: orb_levels[name] = None

        for i in range(45, max_len):
            # 1. CHECK EXITS
            to_close = []
            for name, pos in self.active_positions.items():
                df_day = stock_data_dict[name]
                if i >= len(df_day): continue
                
                row = df_day.iloc[i]
                ltp = row['close']
                ts = row['date']
                e5, e9 = row['ema5'], row['ema9']
                
                # Calculate PnL for TSL tracking
                pnl_pts = (ltp - pos['in']) if pos['type'] == 'LONG' else (pos['in'] - ltp)
                pnl_rs = pnl_pts * LOT_SIZES.get(name, 50)
                pos['max_pnl_rs'] = max(pos.get('max_pnl_rs', 0), pnl_rs)
                
                # Exit Logic
                exit_hit = False
                reason = ""
                
                # A. Technical Reversal
                if pos['type'] == 'LONG' and e5 < e9:
                    exit_hit, reason = True, f"LTP({ltp:.1f}) | EMA5({e5:.1f}) < EMA9({e9:.1f})"
                elif pos['type'] == 'SHORT' and e5 > e9:
                    exit_hit, reason = True, f"LTP({ltp:.1f}) | EMA5({e5:.1f}) > EMA9({e9:.1f})"
                
                # B. EOD Force Square-off
                if ts.time() >= dt_time(15, 15):
                    exit_hit, reason = True, "EOD FORCE EXIT"

                if exit_hit:
                    # Log ENTRY (with split score)
                    self.all_trades.append({
                        'Time': pos['entry_time'], 'Stock': name, 'Action': f"ENTRY ({pos['type']})",
                        'Price': pos['in'], 'PnL_Rs': '-', 'Reason': pos['entry_reason']
                    })
                    # Log EXIT (with detailed values)
                    self.all_trades.append({
                        'Time': ts, 'Stock': name, 'Action': 'SQUARE-OFF',
                        'Price': ltp, 'PnL_Rs': round(pnl_rs, 2), 
                        'Reason': f"{reason} | MaxPnL: {pos['max_pnl_rs']:.0f}"
                    })
                    to_close.append(name)
            
            for name in to_close: del self.active_positions[name]

            # 2. CHECK ENTRIES (Hard Cutoff 14:30)
            if i >= max_len or pd.Timestamp(stock_data_dict[stock_names[0]]['date'].iloc[i]).time() > dt_time(14, 30):
                continue

            if len(self.active_positions) >= self.top_n: continue
            
            candidates = []
            for name in stock_names:
                if name in self.active_positions: continue
                df_day = stock_data_dict[name]
                if i >= len(df_day): continue
                
                row = df_day.iloc[i]
                score, breakdown = self._calc_detailed_score(name, row['close'], row['adx'], orb_levels[name], row)
                
                if abs(score) >= self.threshold:
                    candidates.append({'name': name, 'score': score, 'breakdown': breakdown, 'ltp': row['close'], 'time': row['date']})

            ranked = sorted(candidates, key=lambda x: abs(x['score']), reverse=True)
            for c in ranked:
                if len(self.active_positions) >= self.top_n: break
                self.active_positions[c['name']] = {
                    'in': c['ltp'], 'type': 'LONG' if c['score'] > 0 else 'SHORT', 
                    'entry_time': c['time'], 'entry_reason': c['breakdown'], 'max_pnl_rs': 0
                }

    def _calc_detailed_score(self, name, ltp, adx, orb, row):
        if not orb: return 0, ""
        f1 = 0.25 if ltp > orb['h'] else (-0.25 if ltp < orb['l'] else 0)
        f3 = 0.20 if row['ema5'] > row['ema9'] else -0.20
        f8 = 0.25 if adx > 25 else 0
        
        total = (f1 * self.weights[0]) + (f3 * self.weights[2]) + (f8 * self.weights[7])
        breakdown = f"Score:{total:.2f} (F1:{f1*self.weights[0]:.2f}, F3:{f3*self.weights[2]:.2f}, F8:{f8*self.weights[7]:.2f})"
        return total, breakdown

def generate_enhanced_day_report(target_date_str):
    stocks_dir = "python-trader/backtest_lab/data/stocks/"
    all_files = sorted([f for f in os.listdir(stocks_dir) if f.endswith('_minute.csv')])
    target_stocks = all_files[:50]
    target_date = pd.to_datetime(target_date_str).date()
    
    stock_data = {}
    for filename in target_stocks:
        stock_name = filename.replace('_minute.csv', '')
        loader = DataLoader(os.path.join(stocks_dir, filename))
        df = loader.load_data(days=10)
        closes = df['close'].values.astype(float)
        df['ema5'] = talib.EMA(closes, 5)
        df['ema9'] = talib.EMA(closes, 9)
        df['adx'] = talib.ADX(df['high'].values.astype(float), df['low'].values.astype(float), closes, 14)
        stock_data[stock_name] = df[df['date'].dt.date == target_date].reset_index(drop=True)

    engine = EnhancedPortfolioEngine(top_n=5, threshold=0.35)
    engine.run_simulation(stock_data)
    
    df_trades = pd.DataFrame(engine.all_trades)
    total_pnl = pd.to_numeric(df_trades['PnL_Rs'], errors='coerce').sum()
    
    html_content = f"""
    <html>
    <head>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
            body {{ background-color: #f8f9fa; padding: 20px; font-size: 13px; }}
            .entry-row {{ background-color: #f0f7ff !important; }}
            .exit-row {{ background-color: #fff9f0 !important; border-bottom: 2px solid #dee2e6 !important; }}
            .profit {{ color: green; font-weight: bold; }}
            .loss {{ color: red; font-weight: bold; }}
            .header-card {{ background: #1a237e; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container-fluid">
            <div class="header-card text-center">
                <h2>🦅 NIFTY 50 ELITE PORTFOLIO REPORT</h2>
                <p>Date: {target_date_str} | Entry Cutoff: 14:30 | Logic: Detailed Evidence Logs</p>
                <h3 class="mt-2">Day Total: Rs {total_pnl:,.2f}</h3>
            </div>
            
            <table class="table table-bordered table-sm bg-white">
                <thead class="table-dark">
                    <tr>
                        <th>Time</th>
                        <th>Stock</th>
                        <th>Action</th>
                        <th>Price</th>
                        <th>PnL (Rs)</th>
                        <th>Reasoning & Evidence</th>
                    </tr>
                </thead>
                <tbody>
    """
    for _, row in df_trades.iterrows():
        is_entry = "ENTRY" in row['Action']
        pnl_val = row['PnL_Rs']
        pnl_class = "profit" if (not is_entry and pnl_val > 0) else ("loss" if (not is_entry and pnl_val < 0) else "")
        html_content += f"""
                    <tr class="{'entry-row' if is_entry else 'exit-row'}">
                        <td>{row['Time'].strftime('%H:%M:%S')}</td>
                        <td>{row['Stock']}</td>
                        <td>{row['Action']}</td>
                        <td>{row['Price']:.2f}</td>
                        <td class="{pnl_class}">{pnl_val if not is_entry else '-'}</td>
                        <td>{row['Reason']}</td>
                    </tr>
        """
    html_content += "</tbody></table></div></body></html>"
    
    with open(f"python-trader/backtest_lab/reports/enhanced_day_report_{target_date_str}.html", "w") as f:
        f.write(html_content)
    print(f"✅ Enhanced report generated: python-trader/backtest_lab/reports/enhanced_day_report_{target_date_str}.html")

if __name__ == "__main__":
    generate_enhanced_day_report("2026-01-21")
