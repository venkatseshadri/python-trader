import yaml

# Test your config.yaml
try:
    with open('./config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    print("✅ Config loaded successfully!")
    print("Shoonya credentials:", config['shoonya'].keys())
except Exception as e:
    print("❌ Config error:", e)