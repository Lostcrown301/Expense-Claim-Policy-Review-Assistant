# AGENT_USAGE

How AI tools were used to build this project, where they went wrong, and how the output was verified.

## 1. Tools used

| Tool | Used for |
|---|---|
| Claude (chat) | Architecture and phase planning, drafting the policy / limits / seed data, writing prompts for the coding agent, reviewing the agent's reports |
| Antigravity | Scaffolding, backend modules, tests, frontend implementation, deployment configuration, running commands, debugging, and iterative fixes |
| Groq (OpenAI-compatible API) | **Runtime** LLM inside the app (classification and policy explanation). Not a development tool |

### Runtime model selection

The runtime LLM was initially experimented with using Google Gemini during prompt development. Gemini was later replaced by Groq using the OpenAI-compatible API.

The Gemini experiments were useful for developing and testing the prompt rules, especially around ambiguous claims, but the final application does **not** use Gemini.

The final runtime model configuration is:

```text
LLM_MODELS=openai/gpt-oss-120b,openai/gpt-oss-20b
```

The models are attempted in order so that a temporary failure from one model does not immediately make the AI review unavailable.

### Why I shifted from Gemini to Groq

I initially tested Gemini because it was convenient for early runtime prompt experiments. However, the Gemini API repeatedly produced availability/high-demand problems during development, including `503 UNAVAILABLE` responses.

More importantly, I wanted a predictable provider/model configuration for the final deployed application. I therefore moved the runtime integration to Groq's OpenAI-compatible API and used `gpt-oss-120b` with `gpt-oss-20b` as a fallback model.

This was a reliability and availability decision rather than a claim that Groq was objectively more accurate. Model behavior was still verified using the project's representative claims.

The final application therefore uses Groq, while the earlier Gemini runs are retained in this document as part of the development history and prompt-debugging process.

## 2. Representative prompts

Prompts are summarized here rather than reproduced in full.

- **Phase 0 (skeleton):** FastAPI + Next.js skeleton, `/health`, JSON logging with request IDs, `.env.example`, explicit instruction not to build later phases.
- **Phase 1 (validators):** pure-Python validators driven by `limits.yaml`, citable policy sections, tests against seed claims, and explicit instructions not to commit.
- **Phase 2 (runtime AI experiment):** structured JSON output, policy-only reasoning, category classification, uncertainty handling, citation requirements, and explicit separation between AI reasoning and deterministic validation.
- **Prompt debugging:** ambiguous claims were repeatedly tested and the reasoning was inspected rather than relying only on the final verdict.
- **Audit prompts:** asked the agent to map every required test to a test function and to explain any edit made after a failing run.
- **Runtime prompt versions:** v1 through v5. The later versions added rules for uncertainty, citation relevance, preserving AND conditions, and preventing the LLM from requesting fields handled by deterministic code.

## 3. Work delegated vs. done by hand

### Delegated to Antigravity

- Project scaffolding and initial repository structure
- FastAPI backend implementation
- Deterministic validation modules and tests
- Database models, CRUD operations, and Alembic migrations
- AI service integration and structured output validation
- API endpoints
- Next.js frontend
- Frontend/backend integration
- Deployment configuration
- Debugging and iterative fixes
- Running automated tests, linting, builds, and deployment checks

### Done or decided by me

- Overall architecture and separation between deterministic validation and AI reasoning
- Policy structure and policy assumptions
- Limits and category definitions
- Seed claim scenarios
- Phase-by-phase acceptance criteria
- Which agent suggestions to accept or reject
- Reviewing agent reports and generated diffs
- Manual production QA
- Deployment choices: Render, Neon PostgreSQL, and Vercel
- Final verification of security/secrets handling
- Final review of the deployed application

The brief supplied no official company policy or limits, so the sample policy, limits, and seed claims were drafted as project assumptions with Claude and are editable in `backend/data/`.

## 4. Agent mistakes and rejected suggestions

| # | What went wrong | How I caught it | Resolution |
|---|---|---|---|
| 1 | Phase 0 report said setup was complete, but the frontend health page was still the default Next.js page, `frontend/.env.example` was missing, and `requirements.txt` used unpinned `>=` versions | Verification prompt with a PASS/FAIL checklist | Agent fixed all three |
| 2 | `pytest` passed only with a manual `PYTHONPATH` workaround | Read the command log, not just the summary | Added `backend/pytest.ini` (`pythonpath = .`) |
| 3 | Phase 1 test passed the whole seed list as "existing claims", so claim #1 was flagged as a duplicate of #2 | Agent reported a failing assertion; I asked exactly what changed | Fixed the test setup (empty DB for #1, `[claim_1]` for #2). No assertion was weakened |
| 4 | Tests were coarse (7 bundled tests) and a mutation check was a throwaway script | Reviewed `pytest -v` names | Split into parametrized tests with readable ids; replaced the script with a permanent config-driven test |
| 5 | Agent ran tests on the system Python, not the project venv | Interpreter path in pytest output | Re-ran with `.venv`; noted for future prompts |
| 6 | `create-next-app` created a nested `.git` inside `frontend/`, which would have excluded the frontend from the root repo | `Test-Path frontend\.git` before first commit | Removed the nested repo |
| 7 | Early Gemini experiments encountered unavailable/high-demand models and `503` responses | Runtime generation tests | Gemini was replaced by Groq for the final runtime integration |
| 8 | Runtime LLM prompt v1 on the ambiguous "team thing at the pub" claim: stated guesses as facts (alcohol, no business purpose), compared the amount to a limit it never cited (that check belongs to the validators), missed the "were clients present?" question, and chose `needs_review` where `needs_clarification` was right | Read the reasoning, not just the verdict. Citations were verified as real, but the logic was still flawed | Prompt rules were revised through v2-v5 |
| 9 | A prompt revision removed amount and receipt from the model input, but the model then treated those fields as missing information and asked the reviewer for them | Read claim #9's `missing_info` after the change | Added an explicit rule that amount, date, receipt, and claimant are handled by deterministic code and must never be requested by the LLM |
| 10 | Groq `gpt-oss-120b` handled the deliberately ambiguous pub claim differently from earlier Gemini runs: it consistently returned `needs_review` instead of asking for the missing business purpose/attendees | Ran the same claim three times at temperature 0 | Kept the model behavior as a documented limitation; uncertainty is still determined in code and the claim is routed to human review |
| 11 | A citation could be a real quote from the policy but still fail to actually support the statement being made | Compared reasoning against the cited policy sentence | Added a prompt rule requiring citations to directly support the associated statement; citation existence is also verified in code |
| 12 | The model initially weakened an AND condition in the alcohol rule, effectively treating the approval requirement and 30% cap as alternatives | Reviewed claim #9 reasoning | Added an explicit prompt rule to preserve AND conditions |
| 13 | Frontend deployment initially omitted `frontend/src/lib/api.ts` and `types.ts` because the root `.gitignore` broadly ignored `lib/` | Vercel build failure and Git tracking check | Fixed `.gitignore`, restored the files, and redeployed |
| 14 | New-claim submission redirected to `/claims/undefined` because the API response was nested under `result.claim` while the frontend expected `result.id` | Manual production QA | Fixed the API response typing and frontend redirect |
| 15 | Category validation was case-sensitive, so values such as `Software` could be rejected even though `software` was valid | Production QA | Added schema-level category normalization and tests for different casing/whitespace |
| 16 | The frontend exposed non-canonical category values such as `travel international`, causing deterministic validation failures even though the AI could classify the claim as `travel_intercity` | Manual QA of the new-claim form | Centralized canonical category options and updated the form |
| 17 | The AI could return `complies` even when deterministic validation found a hard policy violation such as exceeding a category limit | Manual QA with a meal claim above the configured limit | Added derived `overall_status`; deterministic failures override an AI `complies` result |
| 18 | A temporary production test claim was created during redirect/API QA | Reviewed production claim list after testing | Identified it as a test artifact and removed/flagged it for cleanup rather than treating it as real data |

## 5. Runtime AI behaviour log

The runtime prompt evolved during development. Gemini was used for some early experiments; the final implementation uses Groq.

| Prompt version | Model | Claim | Result | Notes |
|---|---|---|---|---|
| v1 | Gemini 3.7 Flash | #5 pub | `needs_review`, confidence 0.6, uncertain, citations verified | Prompt incorrectly treated assumptions as facts, compared limits, and missed clarification questions |
| v4 | `openai/gpt-oss-120b` | #5 pub | `needs_review`, confidence 0.90–0.92, uncertain | Stable across 3/3 runs, but still failed to ask for the missing business purpose/attendees |
| v4 | `openai/gpt-oss-120b` | #9 client dinner + wine | `needs_clarification` | Correctly preserved the approval + 30% alcohol-cap condition, but incorrectly asked for amount/receipt |
| v4 | `openai/gpt-oss-120b` | #1 clean dinner | `complies` | Correct; no unnecessary amount/receipt reasoning |
| v5 | `openai/gpt-oss-120b` / fallback chain | Representative claims | Final prompt used in service | Added explicit handling for business-purpose-dependent policies and fields owned by deterministic validation |

### Important runtime design decision

The LLM does **not** perform deterministic checks such as:

- arithmetic
- duplicate detection
- receipt presence
- date validation
- configured monetary limits
- required-field validation

Those checks are performed by Python code.

The LLM is responsible for:

- interpreting ambiguous descriptions
- suggesting a policy category
- explaining relevant policy
- identifying genuinely missing contextual information
- producing policy citations
- reporting classification uncertainty

This separation was kept deliberately even when the LLM could theoretically perform some of the same checks.

## 6. How output was verified

- Deterministic validators cover duplicates, totals, receipts, limits, dates, currencies, required fields, and category validation.
- The final backend test suite contains **62 passing tests**.
- The LLM never approves or rejects a claim. Reviewer actions are the only way a final reviewer decision is recorded.
- A derived `overall_status` combines deterministic validation with the AI result. A deterministic policy failure forces `needs_review` even if the AI says `complies`.
- Every AI citation is checked in code: the quoted text must exist in the cited policy section, and unverified citations are flagged.
- Low-confidence classifications (`< 0.7`) are marked `uncertain` in the application.
- I read the AI's reasoning, not just its structured fields.
- Representative ambiguous claims were run repeatedly to check stability. Claim #5 was run three times at temperature 0 during prompt testing.
- Manual production QA covered:
  1. normal compliant meal
  2. meal exceeding configured limit
  3. intercity claim missing required context
  4. missing receipt
  5. duplicate claim
- All five manual QA scenarios produced the expected overall review behavior.
- Frontend verification included ESLint and production build checks.
- Backend/frontend integration was verified against the deployed Render and Vercel applications.
- Before commits, `git add -n .` was used to inspect staged candidates and `git check-ignore` was used to verify environment files were ignored.
- Agent reports were treated as claims, not facts: tests were re-run in the project environment and diffs were inspected before accepting changes.
- A GitHub secret audit confirmed that real API keys and database credentials were not committed.

## 7. Known limitations

- Model confidence is self-reported and not calibrated.
- LLM behavior can vary between providers/models; the ambiguous pub claim demonstrated this during Gemini vs. Groq testing.
- Free-tier/provider availability can change. The application is designed so AI failure does not prevent deterministic validation or manual reviewer action.
- Policy values are assumptions, not an official company policy.
- Citation verification confirms that a quote exists in the cited section; it does not mathematically prove that an LLM's interpretation of the quote is correct.
- The application does not use a vector database. The policy is small enough that relevant policy context is provided directly to the runtime model.
- There is no production SSO/authentication layer in the current take-home implementation.
- The application does not handle reimbursement, payroll, payment processing, tax calculations, OCR, or automated final approval/rejection.
