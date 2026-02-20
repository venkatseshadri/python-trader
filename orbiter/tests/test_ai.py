from google import genai
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
    client = genai.Client(api_key=api_key)

    print("\n🔍 Listing some compatible models...")
    # The new SDK doesn't have a direct equivalent to list_models in the same way,
    # but we can test the specific models we use.
    
    for model_name in ['gemini-2.0-flash', 'gemini-1.5-flash']:
        print(f"\n🚀 Testing '{model_name}'...")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=f"Say 'Orbiter {model_name} AI Online' if you can hear me."
            )
            print(f"🤖 Response: {response.text.strip()}")
        except Exception as e:
            print(f"❌ {model_name} failed: {e}")

if __name__ == "__main__":
    test_gemini()
