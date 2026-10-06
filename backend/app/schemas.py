from pydantic import BaseModel, ConfigDict
from typing import Any, Literal

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
