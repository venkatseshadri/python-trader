import json
import os
import pandas as pd

def generate_full_csv(root_dir, output_path):
    rows = []
    print(f"📄 Scanning weight-centric scenarios in {root_dir}...")
    
    for batch_folder in sorted(os.listdir(root_dir)):
        batch_path = os.path.join(root_dir, batch_folder)
        if not os.path.isdir(batch_path): continue
        
        for file in sorted(os.listdir(batch_path)):
            if not file.endswith('.json'): continue
            
            with open(os.path.join(batch_path, file)) as f:
                data = json.load(f)
                w = data['config']['weights']
                
                rows.append({
                    'Scenario': data['name'],
                    'F1_Weight': w[0], 'F2_Weight': w[1], 'F3_Weight': w[2],
                    'F4_Weight': w[3], 'F5_Weight': w[4], 'F6_Weight': w[5],
                    'F7_Weight': w[6]
                })

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    print(f"✅ Full CSV generated: {output_path} ({len(df)} scenarios)")

if __name__ == "__main__":
    root = "backtest_lab/scenarios/master_suite"
    out = "backtest_lab/scenarios/all_weight_scenarios.csv"
    generate_full_csv(root, out)
