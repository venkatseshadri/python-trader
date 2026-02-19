import pandas as pd
import json
import os

# Source Files
PRECISION_FILE = "backtest_lab/data/orb_precision_stats.csv"
EFFICIENCY_FILE = "backtest_lab/data/orb_efficiency_stats.csv"
OUTPUT_FILE = "orbiter/data/orb_weights_master.json"

def generate_master_json():
    if not os.path.exists(PRECISION_FILE) or not os.path.exists(EFFICIENCY_FILE):
        print("❌ Error: Study files missing. Run precision and efficiency scripts first.")
        return

    # Load Studies
    df_p = pd.read_csv(PRECISION_FILE)
    df_e = pd.read_csv(EFFICIENCY_FILE)

    # Merge data
    df_master = pd.merge(df_p, df_e[['Symbol', 'Remaining_Alpha_%']], on='Symbol', how='inner')
    
    # Calculate Final Static Score Components
    # Score = (Reliability * Precision) * Potential_Remaining
    # We store the components so the live bot can apply them dynamically
    
    master_dict = {}
    for _, row in df_master.iterrows():
        symbol = row['Symbol']
        master_dict[symbol] = {
            "reliability": round(float(row['Reliability_Recall']), 3),
            "precision": round(float(row['Precision_Factor']), 3),
            "efficiency": round(float(row['Remaining_Alpha_%'] / 100), 3), # as a multiplier
            "last_updated": "2026-02-19"
        }

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(master_dict, f, indent=2)
    
    print(f"✅ Master weights saved to: {OUTPUT_FILE}")
    print(f"📊 Integrated {len(master_dict)} stocks into the lookup master.")

if __name__ == "__main__":
    generate_master_json()
