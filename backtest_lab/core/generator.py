import json
import itertools
import os

class ScenarioGenerator:
    def __init__(self):
        # Base shared defaults
        self.base_config = {
            "entry_start_time": "09:30",
            "entry_end_time": "14:30",
            "trade_threshold": 0.15,
            "sl_pct": 10.0,
            "tsl_activation_rs": 1000,
            "tsl_retracement_pct": 50,
            "weights": [0.0]*7,
            "soft_sl_atr": False
        }

    def generate_weight_configs(self):
        """Standard 0.05-increment weights from previous step (3,299 combos)."""
        f_ids = [1, 2, 3, 4, 5, 6, 7]
        variations = []
        for i in range(1, len(f_ids) + 1):
            for combo in itertools.combinations(f_ids, i):
                active_indices = [fid - 1 for fid in combo]
                n = len(active_indices)
                baseline = [0.0] * 7
                units = 20
                per_filter = units // n
                remainder = units % n
                for idx in active_indices: baseline[idx] = per_filter * 0.05
                for k in range(remainder): baseline[active_indices[k]] += 0.05
                baseline = [round(x, 2) for x in baseline]
                variations.append(baseline)
                if n > 1:
                    for target_idx in active_indices:
                        current = list(baseline)
                        while True:
                            next_v = list(current)
                            next_v[target_idx] = round(min(1.0, next_v[target_idx] + 0.05), 2)
                            others = [idx for idx in active_indices if idx != target_idx]
                            shrunk = False
                            for o_idx in others:
                                if next_v[o_idx] >= 0.05:
                                    next_v[o_idx] = round(next_v[o_idx] - 0.05, 2)
                                    shrunk = True
                                    break
                            if not shrunk: break
                            if next_v not in variations: variations.append(next_v)
                            current = next_v
                            if next_v[target_idx] >= 1.0: break
        return variations

    def generate_risk_profiles(self):
        """Reduced grid based on user feedback: TSL retracement up to 50%."""
        sl_levels = [5.0, 10.0, 15.0]
        tsl_retracements = [25, 50] # Capped at 50% as requested
        
        profiles = []
        for sl in sl_levels:
            for retrace in tsl_retracements:
                profiles.append({
                    'sl_pct': sl,
                    'tsl_retracement_pct': retrace,
                    'soft_sl_atr': False # Disabled to focus on primary risk
                })
        return profiles

    def get_universal_scenarios(self):
        """Returns all paired configurations in memory for the Mass Optimizer."""
        weights = self.generate_weight_configs()
        risks = self.generate_risk_profiles()
        
        scenarios = []
        for i, w in enumerate(weights):
            active_f = "".join([str(idx+1) for idx, val in enumerate(w) if val > 0])
            for j, r in enumerate(risks):
                name = f"F{active_f}_W{i:04d}_R{j:02d}"
                config = self.base_config.copy()
                config.update(r)
                config['weights'] = w
                
                scenarios.append({
                    'name': name,
                    'weights': w,
                    'threshold': config['trade_threshold'],
                    'sl_pct': config['sl_pct'],
                    'config': config # Full config for saving later
                })
        return scenarios

    def save_universal_suite(self, output_root):
        """Generates the massive cross-product of Entry x Risk."""
        weights = self.generate_weight_configs()
        risks = self.generate_risk_profiles()
        
        total = len(weights) * len(risks)
        print(f"🏗️ Building Universal Lab: {len(weights)} Entries x {len(risks)} Risks = {total} Scenarios...")
        
        if not os.path.exists(output_root): os.makedirs(output_root)
        
        count = 0
        for i, w in enumerate(weights):
            active_f = "".join([str(idx+1) for idx, val in enumerate(w) if val > 0])
            
            for j, r in enumerate(risks):
                config = self.base_config.copy()
                config.update(r)
                config['weights'] = w
                
                # Name: F[Combo]_W[W_ID]_R[Risk_ID]
                name = f"F{active_f}_W{i:04d}_R{j:02d}"
                scenario = {"name": name, "config": config}
                
                # Batch every 1000 files
                batch_dir = os.path.join(output_root, f"batch_{count // 1000}")
                if not os.path.exists(batch_dir): os.makedirs(batch_dir)
                
                with open(os.path.join(batch_dir, f"{name}.json"), 'w') as f:
                    json.dump(scenario, f, indent=2)
                count += 1
        
        print(f"✅ Universal Lab Exported: {count} JSON files.")
