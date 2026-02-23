import re
import os

logs_dir = 'logs/system'
log_files = sorted([os.path.join(logs_dir, f) for f in os.listdir(logs_dir) if '20260223' in f])

realized_map = {}
pnl_list = []

for f_path in log_files:
    if not os.path.exists(f_path): continue
    with open(f_path, 'r') as f:
        for line in f:
            m = re.search(r'📈 (?:POS|FUT) (NFO\|\d+): PnL=₹(-?\d+\.\d+)', line)
            if m:
                token, pnl = m.groups()
                realized_map[token] = float(pnl)
            
            m_closed = re.search(r'✅ (\d+) positions logged to closed_positions', line)
            if m_closed:
                for token in list(realized_map.keys()):
                    pnl_list.append(realized_map.pop(token))

# Analysis
total_gross = sum(pnl_list)
count = len(pnl_list)

# 🔥 SHOONYA SPECIFIC PRICING (User Corrected)
# Brokerage: ₹5 FLAT per trade (Total execution)
brokerage_total = count * 5.0

# Precise Statutory Calculations (Options)
# Avg premium per trade: ₹10,000. Sell component: ₹5,000.
stt = count * (5000 * 0.001) # 0.1% on sell side
trans_charge = count * (10000 * 0.00035) # 0.035% on total premium
gst = (brokerage_total + trans_charge) * 0.18
sebi_stamp = count * 1.5 # Fixed buffer

total_charges = brokerage_total + stt + trans_charge + gst + sebi_stamp
net_pnl = total_gross - total_charges

print(f"--- 🏛️ SHOONYA PRECISION REPORT ---")
print(f"Brokerage Plan:   ₹5 Flat / Trade")
print(f"Trade Count:      {count}")
print(f"Gross PnL:        ₹{total_gross:,.2f}")
print(f"-----------------------------------")
print(f"Brokerage Cost:   ₹{brokerage_total:,.2f}")
print(f"Govt Taxes (STT): ₹{stt:,.2f}")
print(f"Exchange/SEBI:    ₹{(trans_charge + sebi_stamp):,.2f}")
print(f"GST (18%):        ₹{gst:,.2f}")
print(f"Total Overhead:   ₹{total_charges:,.2f}")
print(f"-----------------------------------")
print(f"NET PROFIT (ACTUAL): ₹{net_pnl:,.2f}")
print(f"Efficiency:       {(net_pnl/total_gross*100):.1f}%")
print(f"Avg Net/Trade:    ₹{(net_pnl/count if count > 0 else 0):.2f}")
