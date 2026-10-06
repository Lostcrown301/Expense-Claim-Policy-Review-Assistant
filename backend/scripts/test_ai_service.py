import json
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas import ClaimIn
from app.ai_service import review_claim, AIServiceUnavailable


def main():
    load_dotenv()
    claim_no = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    claims = json.loads((Path(__file__).resolve().parent.parent / "data" / "seed_claims.json").read_text())
    claim_dict = claims[claim_no - 1]
    
    claim = ClaimIn(**claim_dict)
    
    print(f"Claim #{claim_no}")
    try:
        review = review_claim(claim)
    except AIServiceUnavailable as e:
        print(f"Error: {e}")
        return
        
    print(f"Category: {review.category}")
    print(f"Confidence: {review.confidence:.2f}")
    print(f"Verdict: {review.verdict}")
    print(f"Uncertain: {review.uncertain}")
    print("\nCitations:")
    for c in review.citations:
        status = "verified" if c.quote_verified else "UNVERIFIED"
        print(f"[{c.section_id}] {status}")
        if not c.quote_verified:
            print(f"  {c.quote}")


if __name__ == "__main__":
    main()
