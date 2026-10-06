from pydantic import BaseModel
from typing import List, Literal

class Citation(BaseModel):
    section_id: str
    quote: str
    quote_verified: bool = False

class AIReview(BaseModel):
    category: str
    confidence: float
    verdict: Literal["complies", "needs_clarification", "needs_review"]
    reasoning: str
    citations: List[Citation]
    missing_info: List[str]
    uncertain: bool = False
    uncertain_reasons: List[str] = []
