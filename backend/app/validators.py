from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from .schemas import ClaimIn, ValidationResult
from .limits import Limits

def validate_claim(claim: ClaimIn, existing_claims: List[Dict[str, Any]], limits: Limits, today: date) -> List[ValidationResult]:
    results = []
    
    # a. required_fields
    missing = []
    for field in ["claimant", "date", "category", "currency", "description"]:
        val = getattr(claim, field, None)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)
    
    if missing:
        results.append(ValidationResult(check="required_fields", status="fail", detail=f"Missing or empty fields: {', '.join(missing)}"))
    else:
        results.append(ValidationResult(check="required_fields", status="pass", detail="All required fields present."))
    
    # Extract properties safely
    parsed_date = None
    if getattr(claim, "date", None):
        try:
            if isinstance(claim.date, str):
                parsed_date = date.fromisoformat(claim.date.strip())
            elif isinstance(claim.date, date):
                parsed_date = claim.date
            elif isinstance(claim.date, datetime):
                parsed_date = claim.date.date()
            else:
                raise ValueError()
                
            delta = (today - parsed_date).days
            if delta < 0:
                results.append(ValidationResult(check="date_valid", status="fail", detail="Date is in the future."))
                parsed_date = None
            elif delta > limits.max_claim_age_days:
                results.append(ValidationResult(check="date_valid", status="fail", detail=f"Date is older than {limits.max_claim_age_days} days."))
                parsed_date = None
            else:
                results.append(ValidationResult(check="date_valid", status="pass", detail="Date is valid."))
        except (ValueError, TypeError):
            results.append(ValidationResult(check="date_valid", status="fail", detail="Unparseable ISO date (YYYY-MM-DD)."))
            
    parsed_amount = None
    if getattr(claim, "amount", None) is not None:
        try:
            val = Decimal(str(claim.amount))
            if val <= 0:
                results.append(ValidationResult(check="amount_valid", status="fail", detail="Amount must be greater than 0."))
            else:
                parsed_amount = val
                results.append(ValidationResult(check="amount_valid", status="pass", detail="Amount is valid."))
        except (InvalidOperation, TypeError, ValueError):
            results.append(ValidationResult(check="amount_valid", status="fail", detail="Amount must be a valid number."))

    parsed_currency = None
    if getattr(claim, "currency", None) is not None and str(claim.currency).strip():
        c = str(claim.currency).strip()
        supported = [s.lower() for s in limits.currency_supported]
        if c.lower() not in supported:
            results.append(ValidationResult(check="currency_supported", status="fail", detail=f"Currency {c} not supported."))
        else:
            parsed_currency = c
            results.append(ValidationResult(check="currency_supported", status="pass", detail="Currency is supported."))
            
    parsed_category = None
    if getattr(claim, "category", None) is not None and str(claim.category).strip():
        cat = str(claim.category).strip()
        if cat not in limits.categories:
            results.append(ValidationResult(check="category_valid", status="fail", detail=f"Category {cat} is unknown."))
        else:
            parsed_category = cat
            results.append(ValidationResult(check="category_valid", status="pass", detail="Category is valid."))

    parsed_claimant = None
    if getattr(claim, "claimant", None) is not None and str(claim.claimant).strip():
        parsed_claimant = str(claim.claimant).strip()
        
    # f. duplicate
    if parsed_claimant is not None and parsed_date is not None and parsed_amount is not None and parsed_category is not None:
        is_duplicate = False
        for idx, ex in enumerate(existing_claims):
            match = True
            for field in limits.duplicate_match_fields:
                ex_val = ex.get(field)
                if ex_val is None:
                    match = False
                    break
                    
                if field == "date":
                    try:
                        ex_val_norm = str(date.fromisoformat(str(ex_val).strip()))
                    except (ValueError, TypeError):
                        match = False
                        break
                    my_val_norm = str(parsed_date)
                elif field == "amount":
                    try:
                        ex_val_norm = Decimal(str(ex_val))
                    except (InvalidOperation, TypeError, ValueError):
                        match = False
                        break
                    my_val_norm = parsed_amount
                else:
                    ex_val_norm = str(ex_val).strip().lower()
                    if field == "claimant": my_val_norm = parsed_claimant.lower()
                    elif field == "category": my_val_norm = parsed_category.lower()
                    elif field == "currency": my_val_norm = parsed_currency.lower() if parsed_currency else ""
                    else:
                        my_val = getattr(claim, field, None)
                        my_val_norm = str(my_val).strip().lower() if my_val else ""
                        
                if ex_val_norm != my_val_norm:
                    match = False
                    break
                    
            if match:
                # Check id to not match against itself
                claim_id = claim.model_extra.get("id") if claim.model_extra else None
                ex_id = ex.get("id")
                
                if claim_id is not None and ex_id is not None and claim_id == ex_id:
                    continue
                
                ex_ident = ex_id if ex_id is not None else str(idx)
                results.append(ValidationResult(check="duplicate", status="fail", detail=f"Duplicate of claim {ex_ident}."))
                is_duplicate = True
                break
                
        if not is_duplicate:
            results.append(ValidationResult(check="duplicate", status="pass", detail="No duplicates found."))

    # g. receipt
    if parsed_amount is not None:
        if parsed_amount > limits.receipt_required_above and not claim.receipt_available:
            results.append(ValidationResult(check="receipt", status="fail", detail=f"Receipt required for amount above {limits.receipt_required_above}."))
        else:
            results.append(ValidationResult(check="receipt", status="pass", detail="Receipt check passed."))

    # h. category_limit_per_claim
    if parsed_category is not None and parsed_amount is not None:
        cat_limits = limits.categories[parsed_category]
        if cat_limits.per_claim is not None:
            if parsed_amount > cat_limits.per_claim:
                results.append(ValidationResult(check="category_limit_per_claim", status="fail", detail=f"Amount {parsed_amount} exceeds per-claim limit {cat_limits.per_claim} for {parsed_category}."))
            else:
                results.append(ValidationResult(check="category_limit_per_claim", status="pass", detail="Within per-claim limit."))
                
    # i. category_limit_per_day
    if parsed_category is not None and parsed_amount is not None and parsed_claimant is not None and parsed_date is not None:
        cat_limits = limits.categories[parsed_category]
        if cat_limits.per_day is not None:
            total_day = parsed_amount
            claim_id = claim.model_extra.get("id") if claim.model_extra else None
                
            for ex in existing_claims:
                ex_id = ex.get("id")
                if claim_id is not None and ex_id is not None and claim_id == ex_id:
                    continue
                    
                ex_claimant = str(ex.get("claimant", "")).strip().lower()
                ex_cat = str(ex.get("category", "")).strip().lower()
                ex_date_raw = ex.get("date")
                
                if ex_claimant == parsed_claimant.lower() and ex_cat == parsed_category.lower():
                    try:
                        ex_date = date.fromisoformat(str(ex_date_raw).strip())
                    except (ValueError, TypeError):
                        continue
                        
                    if ex_date == parsed_date:
                        try:
                            total_day += Decimal(str(ex.get("amount", 0)))
                        except (InvalidOperation, TypeError, ValueError):
                            pass
                            
            if total_day > cat_limits.per_day:
                results.append(ValidationResult(check="category_limit_per_day", status="fail", detail=f"Total day amount {total_day} exceeds per-day limit {cat_limits.per_day} for {parsed_category}."))
            else:
                results.append(ValidationResult(check="category_limit_per_day", status="pass", detail="Within per-day limit."))
                
    # j. approval_threshold
    if parsed_category is not None and parsed_amount is not None:
        cat_limits = limits.categories[parsed_category]
        if cat_limits.approval_required_above is not None:
            if parsed_amount > cat_limits.approval_required_above:
                results.append(ValidationResult(check="approval_threshold", status="warn", detail="needs approval attached"))
            else:
                results.append(ValidationResult(check="approval_threshold", status="pass", detail="Approval threshold not exceeded."))

    return results

def compute_totals(claims: List[Dict[str, Any]]) -> Dict[str, Any]:
    totals = {
        "per_claimant": {},
        "per_category": {},
        "per_claimant_category": {}
    }
    
    for claim in claims:
        claimant = str(claim.get("claimant", "")).strip()
        cat = str(claim.get("category", "")).strip().lower()
        try:
            amt = Decimal(str(claim.get("amount", 0)))
        except (InvalidOperation, TypeError, ValueError):
            continue
            
        if claimant:
            totals["per_claimant"][claimant] = totals["per_claimant"].get(claimant, Decimal('0')) + amt
        if cat:
            totals["per_category"][cat] = totals["per_category"].get(cat, Decimal('0')) + amt
        if claimant and cat:
            key = f"{claimant}|{cat}"
            totals["per_claimant_category"][key] = totals["per_claimant_category"].get(key, Decimal('0')) + amt
            
    return totals

def overall_status(results: List[ValidationResult]) -> str:
    has_warn = False
    for r in results:
        if r.status == "fail":
            return "failed"
        if r.status == "warn":
            has_warn = True
            
    return "warnings" if has_warn else "clean"
