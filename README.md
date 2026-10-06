# Expense Claim Policy Review Assistant

## 1. Overview
The Expense Claim Policy Review Assistant is an internal tool that streamlines the evaluation of employee expense claims. It solves the problem of manual, error-prone policy checking by automatically analyzing claim submissions against the company expense policy. When an employee submits a claim, the system evaluates it using a combination of deterministic validation for objective rules (like limits and duplicates) and AI review for policy interpretation. Ultimately, a human reviewer evaluates the combined findings and makes the final approval or rejection decision.

## 2. Core Workflow
The application follows this end-to-end flow:
1. **Employee submits claim**: Through the UI.
2. **Deterministic validation**: Python backend checks objective rules (limits, dates, receipts, duplicates, required fields).
3. **AI policy review**: An LLM classifies the expense and assesses policy compliance.
4. **Policy evidence/citations**: The AI provides specific quotes from the policy document supporting its reasoning.
5. **Overall review status**: The system synthesizes deterministic and AI findings into a unified status.
6. **Human reviewer decision**: A human reviews the claim in the queue, potentially requesting clarification or overriding the category, and then approves or rejects the claim.
7. **Decision/history persistence**: The final decision and history of actions are saved to PostgreSQL.

*Note: The AI handles classification and policy interpretation. It does NOT own arithmetic or deterministic validation, nor does it approve/reject claims. The final decision is strictly human-controlled.*

## 3. Features / Completed Scope
The following functionality is implemented in the repository:
- **Claim creation**: API and frontend support for submitting new claims.
- **Claim review queue**: A list view of submitted claims with their status.
- **Claim detail view**: Comprehensive breakdown of a single claim.
- **Deterministic validation**: Strict rules-based checking (e.g., receipt requirements, category limits, dates).
- **AI category classification**: Automatic categorization based on claim description.
- **AI confidence**: Confidence score for AI predictions.
- **AI policy reasoning**: Natural language explanation of policy compliance.
- **Policy citations and citation verification**: Exact quotes from the policy document matching the reasoning, verified by the backend.
- **Missing-information questions**: The AI can identify missing context needed for a decision.
- **Overall review status**: Combined status reflecting both AI and deterministic checks.
- **Review actions**: Approve, reject, and request clarification.
- **Category override**: Ability for reviewers to override the AI's category with a reason.
- **Decision history**: Append-only log of reviewer actions.
- **Persistent PostgreSQL storage**: Relational database storage using Neon.
- **Loading/empty/error/success states**: Frontend feedback for async operations.
- **Structured application logging**: Backend request logging with durations.

## 4. Architecture
The application uses a modern web stack with a distinct separation between deterministic logic and AI processing.

```text
Frontend (Next.js + Tailwind)
   ↓
FastAPI Backend
   ├── Deterministic Validators (Python)
   ├── AI Service / LLM (Groq/OpenAI-compatible API)
   ├── Policy Data (Markdown / YAML)
   └── PostgreSQL (Neon) via SQLAlchemy
          ↓
     Review History
```

**Technologies**:
- **Frontend**: Next.js, React, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Pydantic, Python 3.12
- **Database**: PostgreSQL (Neon), SQLAlchemy (ORM), Alembic (Migrations)
- **AI**: Groq API (OpenAI-compatible)

## 5. AI Workflow
The AI service analyzes the claim description to assign a category and determine compliance based on the expense policy.
- **Context Supply**: This project uses the small policy document directly as context in the system prompt rather than introducing unnecessary vector-database/RAG infrastructure.
- **Classification**: The model determines the most appropriate expense category from a predefined list.
- **Structured Output**: The LLM returns a structured JSON response (via Groq/OpenAI format) with verdict, confidence, reasoning, citations, and missing information.
- **Citations**: The AI cites specific sections and exact quotes from the policy document.
- **Verification**: The backend validates that citations exactly match the policy text.
- **Clarification**: The model can determine that a decision cannot be made without further context and output missing info questions.

## 6. Deterministic Validation
Deterministic validation evaluates objective rules independently of the AI. Implemented checks include:
- Required fields (claimant, date, category, currency, description)
- Supported currency
- Category validity
- Claim age/date validation (future dates, maximum age)
- Positive amount numbers
- Duplicate claims
- Receipt requirements based on amount thresholds
- Category limits (per-claim and per-day)
- Approval thresholds

These checks remain deterministic because standard code is more reliable, testable, and efficient for arithmetic, strict rule enforcement, and database lookups than delegating them to an LLM.

## 7. Overall Review Status
The system distinguishes between AI assessment, deterministic validation, and the overall review status.

For example:
An expense can be policy-eligible according to the AI (AI verdict: `complies`), but deterministic validation can still detect a limit violation (Validation: `fail`). In that situation, the overall status becomes `needs_review`.

This separation ensures AI hallucinations cannot bypass strict company limits.

## 8. Human Review
The human reviewer uses the unified findings to make a final decision. Available actions are:
- **Approve**
- **Reject**
- **Request Clarification**
- **Override Category** (requires a reason)

The AI recommendations are advisory and are not final decisions.

## 9. Policy
The project uses a realistic, static project-defined expense policy (as no specific company policy was originally provided).
- **Policy rules**: `backend/data/policy.md`
- **Limits**: `backend/data/limits.yaml`
- **Seed data**: `backend/data/seed_claims.json`

## 10. Data Model / Persistence
The application uses PostgreSQL with SQLAlchemy for data persistence and Alembic for migrations.
Implemented tables:
- `claims`: Core expense claim data.
- `ai_reviews`: AI verdicts, confidence, reasoning, and citations.
- `validation_results`: Outcome of deterministic checks (errors/warnings).
- `decisions`: Append-only history of human reviewer actions (approve, reject, override, etc.).

## 11. Project Structure
```text
backend/
  alembic/       # Database migrations
  app/           # FastAPI application code
  data/          # Policy, limits, and seed data
  scripts/       # Helper scripts (e.g., seed_db.py)
  tests/         # Backend test suite
frontend/
  public/        # Static assets
  src/
    app/         # Next.js App Router pages
```

## 12. Setup / Local Development

### Backend
1. Ensure Python 3.12 is installed.
2. Navigate to the backend directory:
   ```bash
   cd backend
   ```
3. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Copy `.env.example` to `.env` and fill in your values (database URL and LLM API key).
6. Run database migrations:
   ```bash
   alembic upgrade head
   ```
7. (Optional) Seed the database with sample claims:
   ```bash
   python scripts/seed_db.py
   ```
8. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend
1. Ensure Node.js and npm are installed.
2. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
3. Install dependencies:
   ```bash
   npm install
   ```
4. Copy `.env.example` to `.env` (it contains `NEXT_PUBLIC_API_URL=http://localhost:8000`).
5. Start the development server:
   ```bash
   npm run dev
   ```

## 13. Environment Variables
Configuration is managed via environment variables. Note that `.env.example` files contain placeholders only. Real secrets must be supplied locally or via the deployment provider, and no real API keys or database credentials belong in Git.

**Backend (`backend/.env.example`)**:
- `LLM_API_KEY`
- `LLM_MODELS`
- `DATABASE_URL`
- `ALLOWED_ORIGINS`
- `LOG_LEVEL`

**Frontend (`frontend/.env.example`)**:
- `NEXT_PUBLIC_API_URL`

## 14. Testing
The backend is verified using `pytest`.
Currently: **62 tests passing**

The backend test suite covers:
- Core deterministic validation rules
- AI service parsing, retry, and citation verification
- FastAPI route functionality
- Database CRUD operations

## 15. Manual QA
The following key scenarios have been manually verified:
- **Normal compliant meal**: AI verdict `complies`, Validation `pass`, Overall `complies`.
- **Meal exceeding category limit**: AI verdict `complies`, Validation `fail` (exceeds limit), Overall `needs_review`.
- **Intercity travel requiring clarification**: AI verdict `needs_clarification`, Validation `pass`, Overall `needs_clarification`.
- **Missing receipt**: AI verdict `complies`, Validation `fail` (receipt required above limit), Overall `needs_review`.
- **Duplicate claim**: Validation `fail` (duplicate found), Overall `needs_review`.

## 16. Deployment
The application architecture is designed for the following deployment stack:
- **Frontend**: Vercel
- **Backend**: Render (Python 3.12)
- **Database**: Neon PostgreSQL

### Deployment note

The backend is hosted on Render. Because the service may spin down when idle, the **first request after a period of inactivity can take a little longer while the backend starts up**. This is expected behavior for the deployed demo; subsequent requests should respond normally.

### Live Demo
**Frontend**: [https://expense-claim-policy-review-assista-eight.vercel.app/claims](https://expense-claim-policy-review-assista-eight.vercel.app/claims)

**Backend**: [https://expense-claim-policy-review-assistant-1oum.onrender.com](https://expense-claim-policy-review-assistant-1oum.onrender.com)

**Backend health**: [https://expense-claim-policy-review-assistant-1oum.onrender.com/health](https://expense-claim-policy-review-assistant-1oum.onrender.com/health)

## 17. Completed vs Excluded Scope

### Completed
- Claim creation and deterministic validation
- AI-driven policy compliance review with verified citations
- Unified status generation
- Queue and detail views for review
- Human decision actions (Approve, Reject, Clarify, Override)
- Full append-only decision history tracking

### Intentionally Out of Scope
- Production SSO / Authentication (no user login implemented)
- Reimbursement / Payroll / Payment processing
- OCR / Receipt image text extraction
- Tax calculations
- Automatic AI approval/rejection (always requires human review for now)
- Advanced analytics / reporting

## 18. Limitations
- The policy is static and project-defined via markdown files.
- The small policy corpus is suitable for direct context loading, but would need a vector database/RAG approach for massive enterprise policies.
- LLM response quality depends heavily on the chosen model and provider availability.
- No access control or authentication is implemented; any user can view or review claims.
- The current deployment strategy is optimized for a take-home/demo scope rather than a high-availability enterprise production environment.

## 19. Security / Secrets
- Secrets are supplied entirely through environment variables.
- `.env` files are ignored by version control.
- `.env.example` files contain placeholders only.
- The LLM API key and Database credentials reside only in the backend and are not exposed to the frontend.

## 20. License / Notes
No license is specified in this repository.
