from pydantic import BaseModel, ConfigDict
from typing import Any, Literal, List, Optional
from datetime import datetime, date
from .ai_schemas import Citation

class ClaimIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    claimant: Any = None
    date: Any = None
    category: Any = None
    amount: Any = None
    currency: Any = None
    description: Any = None
    receipt_available: bool = False

class ValidationResult(BaseModel):
    check: str
    status: Literal["pass", "fail", "warn"]
    detail: str

class ValidationResultResponse(BaseModel):
    id: int
    claim_id: int
    passed: bool
    errors: List[ValidationResult]
    warnings: List[ValidationResult]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class AIReviewResponse(BaseModel):
    id: int
    claim_id: int
    category: str
    confidence: float
    verdict: str
    reasoning: str
    citations: List[Citation]
    missing_info: List[str]
    uncertain: bool
    uncertain_reasons: List[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class DecisionCreate(BaseModel):
    action: Literal["approve", "reject", "request_clarification", "override_category"]
    reason: Optional[str] = None
    category: Optional[str] = None # Used for override_category

class DecisionResponse(BaseModel):
    id: int
    claim_id: int
    action: str
    reason: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ClaimResponse(BaseModel):
    id: int
    claimant: Optional[str]
    date: Optional[date]
    category: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    description: Optional[str]
    receipt_available: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ClaimListItem(ClaimResponse):
    ai_verdict: Optional[str] = None
    ai_uncertain: Optional[bool] = None
    validation_status: Optional[str] = None
    latest_decision: Optional[str] = None

class ClaimDetailResponse(BaseModel):
    claim: ClaimResponse
    validation: Optional[ValidationResultResponse]
    ai_review: Optional[AIReviewResponse]
    ai_status: str
    history: List[DecisionResponse]

class DecisionHistoryResponse(BaseModel):
    claim_id: int
    history: List[DecisionResponse]

