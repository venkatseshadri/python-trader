import csv
import json
import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, '../backtest_lab/data/orb_efficiency_stats.csv')
BUDGET_MASTER_PATH = os.path.join(BASE_DIR, 'data/budget_master.json')
WEIGHTS_MASTER_PATH = os.path.join(BASE_DIR, 'data/orb_weights_master.json')

def generate_masters():
    if not os.path.exists(CSV_PATH):
        print(f"❌ Error: CSV not found at {CSV_PATH}")
        return

    budget_master = {}
    weights_update = {}

    print(f"📖 Reading {CSV_PATH}...")
    with open(CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            symbol = row['Symbol'].strip().upper()
            
            # 1. Budget Master (Avg_Total_Range_%)
            # We store the raw percentage (e.g., 4.41 for 4.41%)
            try:
                avg_range = float(row['Avg_Total_Range_%'])
                budget_master[symbol] = avg_range
            except ValueError:
                continue

            # 2. Weights Master (Remaining_Alpha_%)
            # Efficiency Score:
            # > 55% -> 1.2 (High Alpha)
            # 50-55% -> 1.0 (Neutral)
            # < 50% -> 0.8 (Low Alpha)
            try:
                rem_alpha = float(row['Remaining_Alpha_%'])
                if rem_alpha >= 55.0:
                    eff_score = 1.2
                elif rem_alpha >= 50.0:
                    eff_score = 1.0
                else:
                    eff_score = 0.8
                
                weights_update[symbol] = {
                    "efficiency": eff_score
                }
            except ValueError:
                continue

    # Save Budget Master
    os.makedirs(os.path.dirname(BUDGET_MASTER_PATH), exist_ok=True)
    with open(BUDGET_MASTER_PATH, 'w') as f:
        json.dump(budget_master, f, indent=4)
    print(f"✅ Generated {BUDGET_MASTER_PATH} ({len(budget_master)} entries)")

    # Update Weights Master
    # Load existing if any
    existing_weights = {}
    if os.path.exists(WEIGHTS_MASTER_PATH):
        with open(WEIGHTS_MASTER_PATH, 'r') as f:
            try:
                existing_weights = json.load(f)
            except: pass
    
    # Merge updates (preserve existing reliability/precision if present, else default)
    for sym, new_data in weights_update.items():
        if sym not in existing_weights:
            existing_weights[sym] = {"reliability": 1.0, "precision": 1.0} # Defaults
        
        existing_weights[sym]['efficiency'] = new_data['efficiency']

    with open(WEIGHTS_MASTER_PATH, 'w') as f:
        json.dump(existing_weights, f, indent=4)
    print(f"✅ Updated {WEIGHTS_MASTER_PATH} ({len(existing_weights)} entries)")

if __name__ == "__main__":
    generate_masters()
