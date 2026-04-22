import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY_POOL", "").split(",")[0]

if not api_key:
    print("❌ No API key found in .env")
    exit()

print(f"Using key starting with: {api_key[:5]}...")
genai.configure(api_key=api_key)

print("\nListing available models:")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name} ({m.display_name})")
except Exception as e:
    print(f"❌ Error listing models: {e}")
