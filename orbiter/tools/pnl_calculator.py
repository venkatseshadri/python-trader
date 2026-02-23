import re
import os

logs_dir = 'logs/system'
log_files = sorted([os.path.join(logs_dir, f) for f in os.listdir(logs_dir) if '20260223' in f])

realized_map = {}
total_realized = 0.0
total_count = 0

for f_path in log_files:
    if not os.path.exists(f_path): continue
    with open(f_path, 'r') as f:
        for line in f:
            # Match PnL update line
            # Example: 2026-02-23 10:51:07,547 | INFO     | 📈 POS NFO|59290: PnL=₹67.50 [Stock: +0.08%] [LTP: 421.00] [Spread: 2.20]
            m = re.search(r'📈 (?:POS|FUT) (NFO\|\d+): PnL=₹(-?\d+\.\d+)', line)
            if m:
                token, pnl = m.groups()
                realized_map[token] = float(pnl)
            
            # Match closure line
            # Example: 2026-02-23 10:51:13,183 | INFO     | ✅ 1 positions logged to closed_positions
            m_closed = re.search(r'✅ (\d+) positions logged to closed_positions', line)
            if m_closed:
                # Every closed position should have a PnL in the map from the previous loop iteration
                # We consume them from the map to calculate realized total
                for token in list(realized_map.keys()):
                    total_realized += realized_map.pop(token)
                    total_count += 1

print(f"--- SESSION REPORT ---")
print(f"Realized PnL: ₹{total_realized:.2f}")
print(f"Trade Count:  {total_count}")
