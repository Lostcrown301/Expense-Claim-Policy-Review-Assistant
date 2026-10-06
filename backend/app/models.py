from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Date, Numeric, JSON
from sqlalchemy.orm import relationship
from .database import Base

def utcnow():
    return datetime.now(timezone.utc)

class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    claimant = Column(String, nullable=True)
    date = Column(Date, nullable=True)
    category = Column(String, nullable=True)
    amount = Column(Numeric, nullable=True)
    currency = Column(String, nullable=True)
    description = Column(String, nullable=True)
    receipt_available = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    ai_reviews = relationship("AIReview", back_populates="claim", cascade="all, delete-orphan")
    validation_results = relationship("ValidationResultModel", back_populates="claim", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="claim", cascade="all, delete-orphan")


class AIReview(Base):
    __tablename__ = "ai_reviews"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    category = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    verdict = Column(String, nullable=False)
    reasoning = Column(String, nullable=False)
    citations = Column(JSON, nullable=False)
    missing_info = Column(JSON, nullable=False)
    uncertain = Column(Boolean, default=False)
    uncertain_reasons = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    claim = relationship("Claim", back_populates="ai_reviews")


class ValidationResultModel(Base):
    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    passed = Column(Boolean, nullable=False)
    errors = Column(JSON, default=[])
    warnings = Column(JSON, default=[])
    created_at = Column(DateTime, default=utcnow)

    claim = relationship("Claim", back_populates="validation_results")


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(Integer, ForeignKey("claims.id"), nullable=False)
    action = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    claim = relationship("Claim", back_populates="decisions")
