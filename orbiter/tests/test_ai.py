import google.generativeai as genai
import yaml
import os

def test_gemini():
    cred_path = "./ShoonyaApi-py/cred.yml"
    if not os.path.exists(cred_path):
        print(f"❌ Credentials not found at {cred_path}")
        return

    with open(cred_path, 'r') as f:
        creds = yaml.safe_load(f)
    
    api_key = creds.get('gemini_api_key')
    if not api_key:
        print("❌ gemini_api_key not found in cred.yml")
        return

    print(f"🔑 Key found: {api_key[:5]}...{api_key[-5:]}")
    genai.configure(api_key=api_key)

    print("\n🔍 Checking available models...")
    try:
        models = genai.list_models()
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                print(f"✅ Available: {m.name}")
    except Exception as e:
        print(f"❌ Error listing models: {e}")

    print("\n🚀 Testing 'gemini-3-flash-preview'...")
    try:
        model = genai.GenerativeModel('gemini-3-flash-preview')
        response = model.generate_content("Say 'Orbiter 3.0-Flash AI Online' if you can hear me.")
        print(f"🤖 Response: {response.text.strip()}")
    except Exception as e:
        print(f"❌ gemini-3-flash-preview failed: {e}")

    print("\n🚀 Testing 'gemini-2.0-flash'...")
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Say 'Orbiter 2.0 AI Online' if you can hear me.")
        print(f"🤖 Response: {response.text.strip()}")
    except Exception as e:
        print(f"❌ gemini-2.0-flash failed: {e}")

    print("\n🚀 Testing 'gemini-1.5-flash-latest'...")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content("Say 'Orbiter 1.5-Latest AI Online' if you can hear me.")
        print(f"🤖 Response: {response.text.strip()}")
    except Exception as e:
        print(f"❌ gemini-1.5-flash-latest failed: {e}")

if __name__ == "__main__":
    test_gemini()
