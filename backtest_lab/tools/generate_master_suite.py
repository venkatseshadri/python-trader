import sys
import os

# Path fix
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backtest_lab.core.generator import ScenarioGenerator

def main():
    output_dir = "backtest_lab/scenarios/master_suite"
    print("\n🚀 Initializing Universal Suite Generation (Entry x Risk)...")
    
    gen = ScenarioGenerator()
    gen.save_universal_suite(output_dir)
    
    print(f"\n📁 Library complete. Root: {output_dir}")
    print("💡 This massive suite allows for simultaneous optimization of Entry and Risk.")

if __name__ == "__main__":
    main()
