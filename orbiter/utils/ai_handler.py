from google import genai
import yaml
import os
import json

class OrbiterAI:
    def __init__(self, cred_path):
        self.api_key = self._load_key(cred_path)
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def _load_key(self, path):
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            creds = yaml.safe_load(f)
        return creds.get('gemini_api_key')

    def ask(self, question, state_context):
        if not self.api_key or not self.client:
            return "⚠️ AI Error: Gemini API key not found or client initialization failed."

        prompt = f"""
You are the AI Expert for the 'Orbiter' Trading Bot.
Your goal is to answer the user's question about the bot's performance or status using the provided internal state data.

INTERNAL STATE:
{json.dumps(state_context, indent=2)}

USER QUESTION:
"{question}"

Please provide a concise, professional, and data-driven explanation in Markdown.
If the question is about why a trade wasn't taken, analyze the filter scores vs the TRADE_SCORE threshold.
"""
        # Try working models only to prevent long hangs
        for model_name in ['gemini-2.0-flash', 'gemini-1.5-flash']:
            try:
                print(f"🤖 AI Attempting Model: {model_name}...")
                response = self.client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                print(f"✅ AI Success with {model_name}")
                return response.text
            except Exception as e:
                print(f"⚠️ AI Model {model_name} failed: {e}")
                # If we hit a quota (429), try the next model
                if "429" in str(e):
                    continue
                continue
        
        return "❌ AI Error: All models failed (likely due to quota limits or 404s). Please try again in a few minutes."
