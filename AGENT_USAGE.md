# AGENT_USAGE

How AI tools were used to build this project, where they went wrong, and how the output was verified.
Items marked **[FILL]** need details only I know. Delete this note when done.

## 1. Tools used

| Tool | Used for |
|---|---|
| Claude (chat) | Architecture and phase planning, drafting the policy / limits / seed data, writing prompts for the coding agent, reviewing the agent's reports |
| **[FILL: coding agent name, e.g. Claude Code / Kiro / Cursor]** | Scaffolding, backend modules, tests, running commands |
| Google Gemini `gemini-3.7-flash` | **Runtime** LLM inside the app (classification and policy explanation). Not a development tool |

Model choice was driven by availability, not benchmarking: `gemini-2.5-flash` was not available for new API users, and `gemini-3.8-flash` returned 503 "high demand" errors during development, so I used `gemini-3.7-flash`.

## 2. Representative prompts

Prompts are summarized; full text is **[FILL: link to a prompts/ folder or paste key ones]**.

- **Phase 0 (skeleton):** FastAPI + Next.js skeleton, `/health`, JSON logging with request IDs, `.env.example`, explicit instruction not to build later phases.
- **Phase 1 (validators):** pure-Python validators driven by `limits.yaml`, citable policy sections, tests against seed claims, "do not commit".
- **Audit prompts:** asked the agent to map every required test to a test function and to explain any edit made after a failing run.
- **Runtime system prompt (v1 -> v2):** see section 5.

## 3. Work delegated vs. done by hand

- Delegated to the agent: **[FILL, e.g. project scaffolding, validators, tests]**
- Done or decided by me: **[FILL, e.g. policy values, deployment choices (Render, Neon, Vercel), reviewing every phase before moving on]**
- Assumption: the brief supplied no policy or limits, so the sample policy, limits and seed claims were drafted with Claude and are editable in `backend/data/`.

## 4. Agent mistakes and rejected suggestions

| # | What went wrong | How I caught it | Resolution |
|---|---|---|---|
| 1 | Phase 0 report said setup was complete, but the frontend health page was still the default Next.js page, `frontend/.env.example` was missing, and `requirements.txt` used unpinned `>=` versions | Verification prompt with a PASS/FAIL checklist | Agent fixed all three |
| 2 | `pytest` passed only with a manual `PYTHONPATH` workaround | Read the command log, not just the summary | Added `backend/pytest.ini` (`pythonpath = .`) |
| 3 | Phase 1 test passed the whole seed list as "existing claims", so claim #1 was flagged as a duplicate of #2 | Agent reported a failing assertion; I asked exactly what changed | Fixed the test setup (empty DB for #1, `[claim_1]` for #2). No assertion was weakened |
| 4 | Tests were coarse (7 bundled tests) and a mutation check was a throwaway script | Reviewed `pytest -v` names | Split into 39 parametrized tests with readable ids; replaced the script with a permanent config-driven test |
| 5 | Agent ran tests on the system Python, not the project venv | Interpreter path in pytest output | Re-ran with `.venv`; noted for future prompts |
| 6 | `create-next-app` created a nested `.git` inside `frontend/`, which would have excluded the frontend from the root repo | `Test-Path frontend\.git` before first commit | Removed the nested repo |
| 7 | Claude (chat) recommended `gemini-2.5-flash`, which was unavailable to new accounts | Generation test failed / model unavailable | Switched model |
| 8 | Runtime LLM prompt v1 on the ambiguous "team thing at the pub" claim: stated guesses as facts (alcohol, no business purpose), compared the amount to a limit it never cited (that check belongs to the validators), missed the "were clients present?" question, and chose `needs_review` where `needs_clarification` was right | Read the reasoning, not just the verdict. All 3 citations were verified real, so the check passed but the logic was still flawed | Prompt v2 (**[FILL: result after testing]**) |

## 5. Runtime AI behaviour log

| Prompt version | Model | Claim | Result | Notes |
|---|---|---|---|---|
| v1 | gemini-3.7-flash | #5 pub | needs_review, confidence 0.6, uncertain, 3/3 citations verified | Problems listed in row 8 above |
| v2 | **[FILL]** | **[FILL]** | **[FILL]** | **[FILL]** |

Provider outage: `gemini-3.8-flash` returned `503 UNAVAILABLE` (high demand). Design response: retry with exponential backoff on 429/500/503, a fallback model, and an explicit "AI unavailable" state so reviewers can still act manually. **[FILL: confirm once implemented]**

## 6. How output was verified

- Deterministic validators (duplicates, totals, receipts, limits, dates) are plain code with 39 automated tests, including a test proving thresholds are read from config.
- The LLM never approves or rejects. Reviewer actions are the only way a claim's status changes.
- Every AI citation is checked in code: the quoted text must exist in the cited policy section, and unverified citations are flagged.
- Low-confidence classifications (< 0.7) are marked "uncertain" in the UI.
- I read the AI's reasoning, not just its structured fields, and ran each seed claim **[FILL: N] times** to check stability.
- Before each commit: `git add -n .` to confirm no secrets or build artifacts, and `git check-ignore` to confirm `.env` is ignored.
- Agent reports were treated as claims, not facts: I re-ran tests in the venv and inspected diffs.

## 7. Known limitations

- Model confidence is self-reported and not calibrated.
- Free-tier LLM quotas and availability can change; the app degrades to manual review when the AI is unavailable.
- Policy values are assumptions, not an official company policy.