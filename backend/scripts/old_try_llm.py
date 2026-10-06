"""Phase 2 experiment: send ONE seed claim to Gemini and inspect the result.

Run from backend/ with the venv active:
    python scripts/try_llm.py 5        # claim number from seed_claims.json (1-11)

Model selection (first match wins):
    LLM_MODELS=gemini-3.7-flash,gemini-3.6-flash   # tried in order (fallback chain)
    LLM_MODEL=gemini-3.7-flash                     # single model

This is a learning script, not production code. Phase 3 moves the useful parts
into app/ai_service.py.
"""
import json
import re
import os
import sys
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Make `import app...` work when running this file directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.limits import load_limits  # noqa: E402
from app.policy import load_policy, quote_exists_in_section  # noqa: E402

load_dotenv()
API_KEY = os.getenv("LLM_API_KEY")
if not API_KEY:
    sys.exit("LLM_API_KEY missing. Run from backend/ and check .env")

_models_env = os.getenv("LLM_MODELS") or os.getenv("LLM_MODEL") or "gemini-3.7-flash"
MODELS = [m.strip() for m in _models_env.split(",") if m.strip()]

RETRYABLE = {429, 500, 502, 503, 504}  # temporary: worth retrying
ATTEMPTS_PER_MODEL = 2                # waits of 3s, 6s, 12s between tries
PROMPT_VERSION = "v3"  # bump this every time you change the prompts below

# ---------------------------------------------------------------- prompts
# The SYSTEM prompt holds standing rules. The USER prompt holds this one claim.
SYSTEM_PROMPT = """You are an assistant that helps a human reviewer check employee expense claims against a company expense policy.

Rules:
1. Use ONLY the policy sections provided. Do not invent policy rules.
2. Classify the claim into one of the allowed categories, based on the description (the claimant's own category may be wrong or vague).
3. Decide a verdict:
   - "complies": the claim clearly follows the policy.
   - "needs_clarification": information is missing or the description is ambiguous.
   - "needs_review": the claim may violate the policy or is a gray area a human must judge.
4. Every finding must cite the policy. For each citation give the section_id and a SHORT quote (under 25 words) copied EXACTLY, word for word, from that section. Never paraphrase inside a quote. section_id must be only the number shown in square brackets, for example "2.2" (not "Section 2.2").
5. If you are unsure of the category, give a LOW confidence (below 0.7) instead of guessing. Confidence is a number from 0 to 1.
6. List any information you would need from the claimant in missing_info (empty list if none).
7. You do NOT approve or reject claims. A human reviewer decides.
8. Do not check arithmetic, duplicates, dates, or receipts. Other code handles those.
9. Do not state as fact anything the claim does not say. If something is unknown (for example whether alcohol was bought or whether a business purpose exists), say it is unknown and put it in missing_info. Use "may" or "could" for unconfirmed concerns.
10. Do not compare amounts to limits. Do not mention numeric limits unless you cite the section they come from.
11. If the outcome depends on missing facts, the verdict must be "needs_clarification", not "needs_review". Use "needs_review" only when the facts are known and a policy conflict or gray area remains.
12. Every statement in your reasoning that relies on a policy rule must have a matching citation.
13. Ask whether clients were present only if the description suggests dining, drinks, or an activity with other people (clients, team, colleagues, guests, a group, entertainment, or a venue such as a pub or bar), and the answer would change which policy section applies.
14. Do not ask about things the description gives no reason to doubt. If the claim clearly matches a policy rule that allows it (for example a train ticket for an approved business trip) and nothing in the description suggests a problem, the verdict is "complies" and missing_info is empty."""


def build_user_prompt(claim: dict, sections: list, categories: list[str]) -> str:
    policy_text = "\n\n".join(f"[{s.id}] {s.title}\n{s.text}" for s in sections)
    claim_view = {k: v for k, v in claim.items() if not k.startswith("_")}
    return (
        f"ALLOWED CATEGORIES: {', '.join(categories)}\n\n"
        f"POLICY:\n{policy_text}\n\n"
        f"CLAIM:\n{json.dumps(claim_view, indent=2)}\n\n"
        "Review this claim."
    )


# ---------------------------------------------------------------- schema
# Tells Gemini the exact JSON shape to return (constrained output).
def response_schema(categories: list[str]) -> dict:
    return {
        "type": "OBJECT",
        "properties": {
            "category": {"type": "STRING", "enum": categories},
            "confidence": {"type": "NUMBER"},
            "verdict": {
                "type": "STRING",
                "enum": ["complies", "needs_clarification", "needs_review"],
            },
            "reasoning": {"type": "STRING"},
            "citations": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "section_id": {"type": "STRING"},
                        "quote": {"type": "STRING"},
                    },
                    "required": ["section_id", "quote"],
                },
            },
            "missing_info": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": ["category", "confidence", "verdict", "reasoning", "citations", "missing_info"],
    }


def post_with_retry(model: str, body: dict) -> httpx.Response | None:
    """POST to one model, retrying temporary failures (429/5xx/timeouts) with
    exponential backoff. Returns the final response, or None if every attempt
    failed at the network level."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    last: httpx.Response | None = None
    for attempt in range(ATTEMPTS_PER_MODEL):
        try:
            last = httpx.post(url, headers={"x-goog-api-key": API_KEY}, json=body, timeout=90)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            print(f"  [{model}] network error ({type(exc).__name__})")
            last = None
        else:
            if last.status_code not in RETRYABLE or last.status_code == 429:
                return last  # success, permanent error, or quota exhausted (retrying won't help)
            print(f"  [{model}] HTTP {last.status_code} (temporary)")
        if attempt < ATTEMPTS_PER_MODEL - 1:
            wait = 3 * 2 ** attempt
            print(f"  retrying in {wait}s (attempt {attempt + 2}/{ATTEMPTS_PER_MODEL})...")
            time.sleep(wait)
    return last


def call_gemini(user_prompt: str, categories: list[str]) -> tuple[dict, str]:
    """Try each model in MODELS in order. Returns (parsed_json, model_used)."""
    body = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.1,  # low = more consistent answers
            "responseMimeType": "application/json",
            "responseSchema": response_schema(categories),
        },
    }

    for i, model in enumerate(MODELS):
        r = post_with_retry(model, body)
        has_next = i < len(MODELS) - 1

        if r is None or r.status_code in RETRYABLE or r.status_code == 404:
            reason = "unreachable" if r is None else f"HTTP {r.status_code}"
            if has_next:
                print(f"  [{model}] giving up ({reason}); falling back to {MODELS[i + 1]}\n")
                continue
            sys.exit(f"All models failed. Last error: {reason}. "
                     "The app should show 'AI unavailable' and let the reviewer continue manually.")

        if r.status_code != 200:  # 400/401/403: bad request or key, fallback won't help
            sys.exit(f"API error {r.status_code}: {r.text[:500]}")

        data = r.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError):
            sys.exit(f"Unexpected response shape (blocked or empty?): {json.dumps(data)[:500]}")
        try:
            return json.loads(text), model
        except json.JSONDecodeError:
            sys.exit(f"Model returned invalid JSON:\n{text[:500]}")

    sys.exit("No model configured.")

def normalize_section_id(raw) -> str:
    """Models sometimes return 'Section 2.2' instead of '2.2'."""
    return re.sub(r"^\s*section\s*", "", str(raw), flags=re.I).strip()

def main() -> None:
    claim_no = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    claims = json.loads((Path(__file__).resolve().parent.parent / "data" / "seed_claims.json").read_text())
    claim = claims[claim_no - 1]

    limits = load_limits()
    categories = list(limits.categories.keys())
    sections = load_policy()
    if isinstance(sections, dict):
        sections = list(sections.values())

    print(f"Models (in order): {', '.join(MODELS)}   Prompt version: {PROMPT_VERSION}")
    print(f"Claim #{claim_no}: {claim['description']!r} ({claim.get('_case', '')})\n")

    result, model_used = call_gemini(build_user_prompt(claim, sections, categories), categories)

    # ------------------------------------------------ verify the AI's output
    threshold = limits.ai_confidence_threshold
    result["uncertain"] = result["confidence"] < threshold

    for c in result["citations"]:
        c["section_id"] = normalize_section_id(c["section_id"])
        c["quote_verified"] = quote_exists_in_section(c["section_id"], c["quote"])

    print(f"Answered by: {model_used}\n")
    print(json.dumps(result, indent=2))
    bad = [c for c in result["citations"] if not c["quote_verified"]]
    print(f"\nUncertain (confidence < {threshold}): {result['uncertain']}")
    print(f"Citations verified: {len(result['citations']) - len(bad)}/{len(result['citations'])}")
    if bad:
        print("UNVERIFIED citations (model quoted text that is not in the policy):")
        for c in bad:
            print(f"  [{c['section_id']}] {c['quote']!r}")


if __name__ == "__main__":
    main()