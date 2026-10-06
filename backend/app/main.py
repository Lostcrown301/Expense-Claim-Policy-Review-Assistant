import time
import uuid
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import get_settings
from app.logging_setup import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title="Expense Claim Policy Review Assistant")

origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()

        response = await call_next(request)

        duration_ms = (time.time() - start_time) * 1000

        extra = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 2)
        }

        logger.info("Request completed", extra=extra)

        return response

app.add_middleware(LoggingMiddleware)

@app.get("/health")
def health_check():
    return {"status": "ok"}
from datetime import date
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from typing import List

from app.database import get_db
from app import crud, schemas, models
from app.validators import validate_claim, overall_status
from app.ai_service import review_claim, AIServiceUnavailable
from app.limits import load_limits

@app.post("/claims", response_model=schemas.ClaimDetailResponse)
def create_claim_endpoint(claim_in: schemas.ClaimIn, db: Session = Depends(get_db)):
    db_claim = crud.create_claim(db, claim_in)
    logger.info("Claim created", extra={"claim_id": db_claim.id})

    existing_claims = crud.get_all_claims_as_dicts(db)
    limits = load_limits()
    today = date.today()

    claim_dict = claim_in.model_dump()
    claim_for_validation = schemas.ClaimIn(**claim_dict)
    claim_for_validation.__pydantic_extra__ = {"id": db_claim.id}

    validation_results = validate_claim(claim_for_validation, existing_claims, limits, today)

    passed = overall_status(validation_results) != "failed"
    errors = [r for r in validation_results if r.status == "fail"]
    warnings = [r for r in validation_results if r.status == "warn"]

    db_vr = crud.create_validation_result(db, db_claim.id, passed, errors, warnings)
    logger.info("Validation completed", extra={"claim_id": db_claim.id, "passed": passed})

    ai_status = "ok"
    db_review = None
    try:
        ai_result = review_claim(claim_in)
        db_review = crud.create_ai_review(db, db_claim.id, ai_result)
        logger.info("AI review success", extra={"claim_id": db_claim.id})
    except AIServiceUnavailable:
        ai_status = "unavailable"
        logger.warning("AI review failure (unavailable)", extra={"claim_id": db_claim.id})
    except Exception as e:
        ai_status = "unavailable"
        logger.error(f"AI review failure: {e}", extra={"claim_id": db_claim.id})

    def _get_overall(v_passed: bool, ai_v: str) -> str:
        if not v_passed: return "needs_review"
        if not ai_v: return "needs_review"
        return ai_v

    return schemas.ClaimDetailResponse(
        claim=db_claim,
        validation=db_vr,
        ai_review=db_review,
        ai_status=ai_status,
        overall_status=_get_overall(passed, db_review.verdict if db_review else None),
        history=[]
    )

@app.get("/claims", response_model=List[schemas.ClaimListItem])
def get_claims_endpoint(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    claims = crud.get_claims(db, skip=skip, limit=limit)

    result = []
    for c in claims:
        latest_review = c.ai_reviews[-1] if c.ai_reviews else None
        latest_validation = c.validation_results[-1] if c.validation_results else None
        latest_decision = c.decisions[-1] if c.decisions else None

        item = schemas.ClaimListItem.model_validate(c)
        if latest_review:
            item.ai_verdict = latest_review.verdict
            item.ai_uncertain = latest_review.uncertain

        passed_val = True
        if latest_validation:
            item.validation_status = "passed" if latest_validation.passed else "failed"
            passed_val = latest_validation.passed

        if latest_decision:
            item.latest_decision = latest_decision.action

        # compute overall
        ai_v = latest_review.verdict if latest_review else None
        if not passed_val:
            item.overall_status = "needs_review"
        else:
            item.overall_status = ai_v if ai_v else "needs_review"

        result.append(item)

    return result

@app.get("/claims/{claim_id}", response_model=schemas.ClaimDetailResponse)
def get_claim_endpoint(claim_id: int, db: Session = Depends(get_db)):
    db_claim = crud.get_claim(db, claim_id)
    if not db_claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    latest_review = db_claim.ai_reviews[-1] if db_claim.ai_reviews else None
    latest_validation = db_claim.validation_results[-1] if db_claim.validation_results else None

    ai_status = "ok" if latest_review else "unavailable"

    passed_val = latest_validation.passed if latest_validation else True
    ai_v = latest_review.verdict if latest_review else None
    overall_status_str = ai_v if passed_val and ai_v else "needs_review"

    return schemas.ClaimDetailResponse(
        claim=db_claim,
        validation=latest_validation,
        ai_review=latest_review,
        ai_status=ai_status,
        overall_status=overall_status_str,
        history=db_claim.decisions
    )

@app.post("/claims/{claim_id}/decision", response_model=schemas.DecisionResponse)
def create_decision_endpoint(claim_id: int, decision: schemas.DecisionCreate, db: Session = Depends(get_db)):
    db_claim = crud.get_claim(db, claim_id)
    if not db_claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    if decision.action == "override_category":
        if not decision.category:
            raise HTTPException(status_code=422, detail="Category is required for override_category")
        if not decision.reason:
            raise HTTPException(status_code=422, detail="Reason is required for override_category")

        limits = load_limits()
        if decision.category not in limits.categories:
            raise HTTPException(status_code=422, detail=f"Category {decision.category} is unknown")

    elif decision.action == "request_clarification":
        if not decision.reason:
            raise HTTPException(status_code=422, detail="Reason is required for request_clarification")

    db_decision = crud.create_decision(db, claim_id, decision)
    logger.info("Decision recorded", extra={"claim_id": claim_id, "action": decision.action})
    return db_decision

@app.get("/claims/{claim_id}/history", response_model=schemas.DecisionHistoryResponse)
def get_claim_history_endpoint(claim_id: int, db: Session = Depends(get_db)):
    db_claim = crud.get_claim(db, claim_id)
    if not db_claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    return schemas.DecisionHistoryResponse(
        claim_id=claim_id,
        history=db_claim.decisions
    )
