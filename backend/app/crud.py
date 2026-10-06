from sqlalchemy.orm import Session
from datetime import date
from . import models, schemas
from decimal import Decimal

def create_claim(db: Session, claim: schemas.ClaimIn) -> models.Claim:
    parsed_date = None
    if claim.date:
        try:
            parsed_date = date.fromisoformat(str(claim.date).strip())
        except (ValueError, TypeError):
            pass

    parsed_amount = None
    if claim.amount is not None:
        try:
            parsed_amount = Decimal(str(claim.amount))
        except:
            pass

    db_claim = models.Claim(
        claimant=str(claim.claimant) if claim.claimant else None,
        date=parsed_date,
        category=str(claim.category) if claim.category else None,
        amount=parsed_amount,
        currency=str(claim.currency) if claim.currency else None,
        description=str(claim.description) if claim.description else None,
        receipt_available=claim.receipt_available
    )
    db.add(db_claim)
    db.commit()
    db.refresh(db_claim)
    return db_claim

def get_claims(db: Session, skip: int = 0, limit: int = 50):
    return db.query(models.Claim).order_by(models.Claim.created_at.desc()).offset(skip).limit(limit).all()

def get_claim(db: Session, claim_id: int):
    return db.query(models.Claim).filter(models.Claim.id == claim_id).first()

def get_all_claims_as_dicts(db: Session):
    claims = db.query(models.Claim).all()
    result = []
    for c in claims:
        d = {
            "id": c.id,
            "claimant": c.claimant,
            "date": c.date.isoformat() if c.date else None,
            "category": c.category,
            "amount": float(c.amount) if c.amount is not None else None,
            "currency": c.currency,
            "description": c.description,
            "receipt_available": c.receipt_available
        }
        result.append(d)
    return result

def create_validation_result(db: Session, claim_id: int, passed: bool, errors: list, warnings: list):
    db_vr = models.ValidationResultModel(
        claim_id=claim_id,
        passed=passed,
        errors=[e.model_dump() for e in errors],
        warnings=[w.model_dump() for w in warnings]
    )
    db.add(db_vr)
    db.commit()
    db.refresh(db_vr)
    return db_vr

def create_ai_review(db: Session, claim_id: int, review):
    db_review = models.AIReview(
        claim_id=claim_id,
        category=review.category,
        confidence=review.confidence,
        verdict=review.verdict,
        reasoning=review.reasoning,
        citations=[c.model_dump() for c in review.citations],
        missing_info=review.missing_info,
        uncertain=review.uncertain,
        uncertain_reasons=review.uncertain_reasons
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review

def create_decision(db: Session, claim_id: int, decision: schemas.DecisionCreate):
    db_decision = models.Decision(
        claim_id=claim_id,
        action=decision.action,
        reason=decision.reason
    )
    db.add(db_decision)
    db.commit()
    db.refresh(db_decision)
    return db_decision
