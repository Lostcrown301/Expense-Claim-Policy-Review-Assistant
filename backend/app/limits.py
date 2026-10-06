import yaml
from pydantic import BaseModel
from typing import Dict, List, Optional
from functools import lru_cache
from pathlib import Path
from decimal import Decimal

class CategoryLimits(BaseModel):
    per_claim: Optional[Decimal] = None
    per_day: Optional[Decimal] = None
    approval_required_above: Optional[Decimal] = None

class Limits(BaseModel):
    currency_supported: List[str]
    receipt_required_above: Decimal
    max_claim_age_days: int
    ai_confidence_threshold: float
    duplicate_match_fields: List[str]
    categories: Dict[str, CategoryLimits]

@lru_cache(maxsize=1)
def load_limits(path: Optional[str] = None) -> Limits:
    if path is None:
        path = str(Path(__file__).parent.parent / "data" / "limits.yaml")
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    return Limits(**data)
