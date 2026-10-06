import json
import os
import re
import time
from typing import Any

import httpx
from pydantic import ValidationError

from .ai_schemas import AIReview, Citation
from .schemas import ClaimIn
from .limits import load_limits
from .policy import load_policy, quote_exists_in_section


class AIServiceUnavailable(Exception):
    pass


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
SERVER_ERRORS = {500, 502, 503, 504}
ATTEMPTS_PER_MODEL = 3
MAX_RATE_LIMIT_WAIT = 20
PROMPT_VERSION = "v5"

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
14. Do not ask about things the description gives no reason to doubt. If the claim clearly matches a policy rule that allows it (for example a train ticket for an approved business trip) and nothing in the description suggests a problem, the verdict is "complies" and missing_info is empty.
15. When you restate a policy rule, keep all of its conditions. If a rule requires two things (for example approval AND a spending cap), say both are required. Never turn "and" into "or".
16. If the description fits more than one policy section, ask the question that would decide which section applies.
17. A citation must directly support the specific statement it is attached to. Do not cite a section just because it mentions a related topic.
18. If the policy section that applies makes a documented business purpose a condition for reimbursement (or excludes the claim without one), and the description does not state a purpose, you cannot know whether one exists. Treat that as missing information: the verdict is "needs_clarification", and missing_info must ask for the business purpose and who attended.
19. The claim amount, date, receipt, and claimant are checked by separate code and are intentionally not shown to you. Never ask for them, never list them as missing, and never mention receipts or amounts in your reasoning."""


def build_user_prompt(claim: ClaimIn, sections: list, categories: list[str]) -> str:
    policy_text = "\n\n".join(f"[{s.id}] {s.title}\n{s.text}" for s in sections)
    claim_view = {
        "claimed_category": claim.category,
        "description": claim.description,
    }
    return (
        f"ALLOWED CATEGORIES: {', '.join(categories)}\n\n"
        f"POLICY:\n{policy_text}\n\n"
        f"CLAIM:\n{json.dumps(claim_view, indent=2)}\n\n"
        "Review this claim."
    )


def response_schema(categories: list[str]) -> dict:
    return {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": categories},
            "confidence": {"type": "number"},
            "verdict": {
                "type": "string",
                "enum": ["complies", "needs_clarification", "needs_review"],
            },
            "reasoning": {"type": "string"},
            "citations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section_id": {"type": "string"},
                        "quote": {"type": "string"},
                    },
                    "required": ["section_id", "quote"],
                    "additionalProperties": False,
                },
            },
            "missing_info": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["category", "confidence", "verdict", "reasoning", "citations", "missing_info"],
        "additionalProperties": False,
    }


def normalize_section_id(raw: Any) -> str:
    return re.sub(r"^\s*section\s*", "", str(raw), flags=re.I).strip()


def _post_process_review(review: AIReview, claim: ClaimIn, limits: Any) -> None:
    threshold = limits.ai_confidence_threshold
    claimed = str(claim.category).strip().lower() if getattr(claim, "category", None) is not None else ""
    
    reasons = []
    if review.confidence < threshold:
        reasons.append(f"confidence {review.confidence} is below {threshold}")
    if claimed and review.category.lower() != claimed:
        reasons.append(f"AI category '{review.category}' differs from claimed '{claimed}'")
    if review.category.lower() == "other":
        reasons.append("AI could not map the claim to a specific policy category")
        
    review.uncertain = bool(reasons)
    review.uncertain_reasons = reasons
    
    for c in review.citations:
        c.section_id = normalize_section_id(c.section_id)
        c.quote_verified = quote_exists_in_section(c.section_id, c.quote)


def review_claim(claim: ClaimIn) -> AIReview:
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise AIServiceUnavailable("LLM_API_KEY missing.")

    _models_env = os.getenv("LLM_MODELS") or os.getenv("LLM_MODEL") or "openai/gpt-oss-120b"
    models = [m.strip() for m in _models_env.split(",") if m.strip()]

    limits = load_limits()
    categories = list(limits.categories.keys())
    sections = load_policy()
    
    user_prompt = build_user_prompt(claim, sections, categories)

    for model in models:
        for attempt in range(ATTEMPTS_PER_MODEL):
            body = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "expense_review",
                        "schema": response_schema(categories),
                    },
                },
            }
            try:
                r = httpx.post(
                    GROQ_URL,
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=body,
                    timeout=90,
                )
            except (httpx.TimeoutException, httpx.TransportError):
                wait = 3 * 2 ** attempt
                if attempt < ATTEMPTS_PER_MODEL - 1:
                    time.sleep(wait)
                continue

            if r.status_code == 429:
                try:
                    wait = float(r.headers.get("retry-after", "5"))
                except ValueError:
                    wait = 5.0
                if wait > MAX_RATE_LIMIT_WAIT:
                    break  # Wait is too long, give up on this model, go to next
                if attempt < ATTEMPTS_PER_MODEL - 1:
                    time.sleep(wait)
                continue

            if r.status_code in SERVER_ERRORS or r.status_code == 404:
                wait = 3 * 2 ** attempt
                if attempt < ATTEMPTS_PER_MODEL - 1:
                    time.sleep(wait)
                continue

            if r.status_code != 200:
                raise AIServiceUnavailable(f"API error {r.status_code}: {r.text[:600]}")

            data = r.json()
            try:
                choice = data["choices"][0]
                text = choice["message"].get("content") or ""
                if not text.strip():
                    raise ValueError("Empty text")
                
                parsed = json.loads(text)
                review = AIReview(**parsed)
                
                _post_process_review(review, claim, limits)
                return review
                
            except (KeyError, IndexError, ValueError, json.JSONDecodeError, ValidationError):
                wait = 3 * 2 ** attempt
                if attempt < ATTEMPTS_PER_MODEL - 1:
                    time.sleep(wait)
                continue
                
    raise AIServiceUnavailable("All models failed.")
