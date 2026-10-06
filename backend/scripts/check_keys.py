import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()  # reads backend/.env
key = os.getenv("LLM_API_KEY")
if not key:
    sys.exit("LLM_API_KEY not found. Check backend/.env and run from backend/.")

BASE = "https://generativelanguage.googleapis.com/v1beta"
headers = {"x-goog-api-key": key}

# Step 1: list models this key can use
r = httpx.get(f"{BASE}/models", headers=headers, timeout=30)
print("List models status:", r.status_code)
if r.status_code != 200:
    sys.exit(r.text[:300])

names = [
    m["name"]
    for m in r.json().get("models", [])
    if "generateContent" in m.get("supportedGenerationMethods", [])
]
print("\nFlash models available:")
for n in names:
    if "flash" in n:
        print(" ", n)

# Step 2: make one real generation call
model = sys.argv[1] if len(sys.argv) > 1 else None
if not model:
    sys.exit("\nRe-run with a model name from the list above, e.g.:\n"
             "  python scripts/check_key.py models/<name-from-list>")

body = {"contents": [{"parts": [{"text": "Reply with exactly: key works"}]}]}
r = httpx.post(f"{BASE}/{model}:generateContent", headers=headers, json=body, timeout=60)
print("\nGenerate status:", r.status_code)
print(r.text[:400] if r.status_code != 200
      else r.json()["candidates"][0]["content"]["parts"][0]["text"])