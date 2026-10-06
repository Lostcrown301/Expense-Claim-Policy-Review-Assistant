import json
import pytest
from datetime import date
from decimal import Decimal
from pathlib import Path
from pydantic import ValidationError

from app.schemas import ClaimIn
from app.limits import load_limits, Limits
from app.validators import validate_claim, compute_totals, overall_status
from app.policy import load_policy, quote_exists_in_section

@pytest.fixture
def test_data_dir():
    return Path(__file__).parent.parent / "data"

@pytest.fixture
def limits(test_data_dir):
    return load_limits(str(test_data_dir / "limits.yaml"))

@pytest.fixture
def seed_claims(test_data_dir):
    with open(test_data_dir / "seed_claims.json", "r", encoding="utf-8") as f:
        # We assign artificial ids to map to the 1-based indexing in instructions
        claims = json.load(f)
        for i, c in enumerate(claims, start=1):
            c["id"] = i
            c.pop("_case", None)
        return claims

def get_claim_by_id(claims, cid):
    for c in claims:
        if c["id"] == cid:
            return c
    return None

@pytest.mark.parametrize("claim_id, check_type, expected_status", [
    (1, "clean", "clean"),
    (2, "duplicate", "fail"),
    (3, "receipt", "fail"),
    (4, "category_limit_per_claim", "fail"),
    (6, "date_valid", "fail"),
    (7, "date_valid", "fail"),
    (8, "approval_threshold", "warn"),
    (10, "clean", "clean"),
    (11, "required_fields", "fail"),
], ids=[
    "1_clean",
    "2_duplicate",
    "3_missing_receipt",
    "4_over_category_limit",
    "6_future_date",
    "7_older_than_60_days",
    "8_needs_approval",
    "10_late_night_cab_clean",
    "11_missing_required_fields"
])
def test_seed_claims(seed_claims, limits, claim_id, check_type, expected_status):
    today = date(2026, 10, 5)
    
    claim_dict = get_claim_by_id(seed_claims, claim_id)
    claim = ClaimIn(**claim_dict)
    
    # We must treat claim #1 as an existing claim when validating #2.
    # To strictly maintain the original assertion without weakening it,
    # we pass all claims but ensure duplicate logic works as requested.
    # Wait, passing all claims causes claim #1 to fail because it matches claim #2.
    # We'll pass the claims up to the current claim as 'existing_claims'.
    # Or, as I previously did, just pass an empty list for everything except #2.
    # The prompt explicitly said: "Treat claim #1 as an existing claim when validating #2."
    # So we'll pass [get_claim_by_id(seed_claims, 1)] for claim_id == 2, and [] for others,
    # or pass seed_claims but filter properly.
    if claim_id == 2:
        existing = [get_claim_by_id(seed_claims, 1)]
    else:
        existing = []

    res = validate_claim(claim, existing, limits, today)
    
    if expected_status == "clean":
        assert overall_status(res) == "clean"
        assert not any(r.status == "fail" for r in res)
    elif check_type == "approval_threshold" and expected_status == "warn":
        assert overall_status(res) == "warnings"
        assert any(r.check == check_type and r.status == expected_status for r in res)
        assert not any(r.status == "fail" for r in res)
    elif claim_id == 11:
        assert any(r.check == "required_fields" and r.status == "fail" for r in res)
        assert any(r.check == "amount_valid" and r.status == "fail" for r in res)
    else:
        assert any(r.check == check_type and r.status == expected_status for r in res)


@pytest.mark.parametrize("check, claim_overrides, expected_status", [
    ("required_fields", {"claimant": ""}, "fail"),
    ("required_fields", {"claimant": "A"}, "pass"),
    ("date_valid", {"date": "invalid"}, "fail"),
    ("date_valid", {"date": "2026-10-01"}, "pass"),
    ("amount_valid", {"amount": -10}, "fail"),
    ("amount_valid", {"amount": 100}, "pass"),
    ("currency_supported", {"currency": "USD"}, "fail"),
    ("currency_supported", {"currency": "INR"}, "pass"),
    ("category_valid", {"category": "unknown_cat"}, "fail"),
    ("category_valid", {"category": "meals"}, "pass"),
    ("receipt", {"amount": 600, "receipt_available": False}, "fail"),
    ("receipt", {"amount": 600, "receipt_available": True}, "pass"),
    ("category_limit_per_claim", {"category": "meals", "amount": 1600}, "fail"),
    ("category_limit_per_claim", {"category": "meals", "amount": 1400}, "pass"),
    ("approval_threshold", {"category": "software", "amount": 5100}, "warn"),
    ("approval_threshold", {"category": "software", "amount": 4900}, "pass"),
], ids=[
    "required_fields_fail", "required_fields_pass",
    "date_valid_fail", "date_valid_pass",
    "amount_valid_fail", "amount_valid_pass",
    "currency_supported_fail", "currency_supported_pass",
    "category_valid_fail", "category_valid_pass",
    "receipt_fail", "receipt_pass",
    "per_claim_limit_fail", "per_claim_limit_pass",
    "approval_threshold_warn", "approval_threshold_pass"
])
def test_validators_in_isolation(limits, check, claim_overrides, expected_status):
    today = date(2026, 10, 5)
    base_dict = {
        "id": 99,
        "claimant": "TestUser",
        "date": "2026-10-01",
        "category": "meals",
        "amount": 100,
        "currency": "INR",
        "description": "Lunch",
        "receipt_available": True
    }
    base_dict.update(claim_overrides)
    claim = ClaimIn(**base_dict)
    
    res = validate_claim(claim, [], limits, today)
    assert any(r.check == check and r.status == expected_status for r in res)

def test_validators_in_isolation_duplicate(limits):
    today = date(2026, 10, 5)
    base_dict = {
        "id": 99, "claimant": "TestUser", "date": "2026-10-01", "category": "meals",
        "amount": 100, "currency": "INR", "description": "Lunch"
    }
    claim = ClaimIn(**base_dict)
    
    # passing
    res_pass = validate_claim(claim, [], limits, today)
    assert any(r.check == "duplicate" and r.status == "pass" for r in res_pass)
    
    # failing
    existing = [base_dict.copy()]
    existing[0]["id"] = 100 # different id but matching fields
    res_fail = validate_claim(claim, existing, limits, today)
    assert any(r.check == "duplicate" and r.status == "fail" for r in res_fail)

def test_validators_in_isolation_per_day(limits):
    today = date(2026, 10, 5)
    base_dict = {
        "id": 99, "claimant": "TestUser", "date": "2026-10-01", "category": "meals",
        "amount": 2000, "currency": "INR", "description": "Lunch"
    }
    claim = ClaimIn(**base_dict)
    
    existing = [{
        "id": 100, "claimant": "TestUser", "date": "2026-10-01", "category": "meals",
        "amount": 1000
    }]
    
    # failing (2000 + 1000 = 3000 > 2500 limit)
    res_fail = validate_claim(claim, existing, limits, today)
    assert any(r.check == "category_limit_per_day" and r.status == "fail" for r in res_fail)
    
    # passing (2000 + 0 = 2000 < 2500 limit)
    res_pass = validate_claim(claim, [], limits, today)
    assert any(r.check == "category_limit_per_day" and r.status == "pass" for r in res_pass)

def test_per_day_limit_accumulation(limits):
    today = date(2026, 10, 5)
    existing_claims = [
        {"id": 100, "claimant": "UserA", "date": "2026-10-01", "category": "meals", "amount": 1000},
        {"id": 101, "claimant": "UserA", "date": "2026-10-01", "category": "meals", "amount": 1000}
    ]
    # new claim pushing over 2500 per_day limit
    claim = ClaimIn(id=102, claimant="UserA", date="2026-10-01", category="meals", amount=600, currency="INR", description="D", receipt_available=True)
    res = validate_claim(claim, existing_claims, limits, today)
    assert any(r.check == "category_limit_per_day" and r.status == "fail" for r in res)

@pytest.mark.parametrize("section_id, quote, expected", [
    ("2.1", "Meals on regular office days are not reimbursable.", True),
    ("2.1", "This is not in the text", False),
    ("2.1", "  mEaLs ON Regular   oFfIcE DaYs ArE NOt rEiMbUrSaBLe. ", True),
    ("2.1", "Meals are reimbursable when the employee is traveling", True),
    ("99.9", "Meals on regular office days are not reimbursable.", False),
], ids=["exact_match", "mismatch", "extra_whitespace_and_case", "different_case_substring", "wrong_section_id"])
def test_quote_exists_in_section(test_data_dir, section_id, quote, expected):
    p = str(test_data_dir / "policy.md")
    assert quote_exists_in_section(section_id, quote, p) == expected

def test_policy_parsing(test_data_dir):
    p = str(test_data_dir / "policy.md")
    sections = load_policy(p)
    sec_ids = [s.id for s in sections]
    assert "1.1" in sec_ids
    assert "2.1" in sec_ids
    assert "10.1" in sec_ids
    for s in sections:
        assert s.text.strip() != "", f"Section {s.id} has empty text"

def test_limits_loading_malformed_config(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("categories: \n  meals: 'not an object'")
    with pytest.raises(ValidationError):
        load_limits(str(f))

def test_compute_totals():
    claims = [
        {"claimant": "A", "category": "meals", "amount": 10},
        {"claimant": "B", "category": "meals", "amount": "20.5"},
        {"claimant": "A", "category": "travel", "amount": 100},
        {"claimant": "A", "category": "meals", "amount": 5}
    ]
    totals = compute_totals(claims)
    assert totals["per_claimant"]["A"] == Decimal("115")
    assert totals["per_claimant"]["B"] == Decimal("20.5")
    assert totals["per_category"]["meals"] == Decimal("35.5")
    assert totals["per_claimant_category"]["A|meals"] == Decimal("15")

def test_receipt_threshold_is_config_driven(tmp_path, test_data_dir, seed_claims, limits):
    import yaml
    
    # Prove it fails with real config
    c3_dict = get_claim_by_id(seed_claims, 3)
    c3 = ClaimIn(**c3_dict)
    res_real = validate_claim(c3, [], limits, date(2026, 10, 5))
    assert any(r.check == "receipt" and r.status == "fail" for r in res_real)
    
    # Mutate limits in a tmp_path copy
    real_limits_path = test_data_dir / "limits.yaml"
    with open(real_limits_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        
    data["receipt_required_above"] = 5000
    tmp_limits_path = tmp_path / "limits.yaml"
    with open(tmp_limits_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f)
        
    # Load modified limits
    mutated_limits = load_limits(str(tmp_limits_path))
    
    # Assert it passes with mutated limits
    res_mutated = validate_claim(c3, [], mutated_limits, date(2026, 10, 5))
    assert not any(r.check == "receipt" and r.status == "fail" for r in res_mutated)
    assert any(r.check == "receipt" and r.status == "pass" for r in res_mutated)

def test_overall_status():
    from app.schemas import ValidationResult
    
    # clean
    assert overall_status([
        ValidationResult(check="1", status="pass", detail="")
    ]) == "clean"
    
    # warnings
    assert overall_status([
        ValidationResult(check="1", status="pass", detail=""),
        ValidationResult(check="2", status="warn", detail="")
    ]) == "warnings"
    
    # failed
    assert overall_status([
        ValidationResult(check="1", status="pass", detail=""),
        ValidationResult(check="2", status="warn", detail=""),
        ValidationResult(check="3", status="fail", detail="")
    ]) == "failed"


@pytest.mark.parametrize("category_input, expected_status", [
    ("software", "pass"),
    ("Software", "pass"),
    ("SOFTWARE", "pass"),
    (" software ", "pass"),
    ("unknown_cat", "fail"),
])
def test_category_normalization(limits, category_input, expected_status):
    today = date(2026, 10, 5)
    base_dict = {
        "id": 99,
        "claimant": "TestUser",
        "date": "2026-10-01",
        "category": category_input,
        "amount": 100,
        "currency": "INR",
        "description": "Software test",
        "receipt_available": True
    }
    claim = ClaimIn(**base_dict)
    
    res = validate_claim(claim, [], limits, today)
    assert any(r.check == "category_valid" and r.status == expected_status for r in res)
