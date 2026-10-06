import json
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

def main():
    load_dotenv()
    
    seed_file = Path(__file__).resolve().parent.parent / "data" / "seed_claims.json"
    claims_data = json.loads(seed_file.read_text())
    
    client = TestClient(app)
    
    print("Seeding database...")
    
    response = client.get("/claims?limit=100")
    existing_descriptions = set(c.get("description") for c in response.json())
    
    seeded_count = 0
    ai_count = 0
    ai_unavailable = 0
    
    for claim_dict in claims_data:
        if claim_dict.get("description") in existing_descriptions:
            continue
            
        res = client.post("/claims", json=claim_dict)
        if res.status_code == 200:
            seeded_count += 1
            data = res.json()
            if data.get("ai_review") is not None:
                ai_count += 1
            elif data.get("ai_status") == "unavailable":
                ai_unavailable += 1
        else:
            print(f"Failed to seed claim: {res.text}")
            
    print(f"Seeded: {seeded_count} claims")
    print(f"AI reviews: {ai_count}")
    print(f"AI unavailable: {ai_unavailable}")

if __name__ == "__main__":
    main()
