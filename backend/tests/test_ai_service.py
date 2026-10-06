import pytest
import os
import httpx
from unittest.mock import patch, MagicMock
from app.ai_service import review_claim, AIServiceUnavailable
from app.schemas import ClaimIn

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "fake_key")
    monkeypatch.setenv("LLM_MODELS", "fake-model-1,fake-model-2")

def mock_httpx_post(status_code=200, json_data=None, raise_exc=None):
    if raise_exc:
        mock = MagicMock()
        mock.side_effect = raise_exc
        return mock
    
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if json_data:
        mock_resp.json.return_value = json_data
    
    mock = MagicMock()
    mock.return_value = mock_resp
    return mock

def get_valid_json(category="meals", verdict="complies", confidence=0.9, section_id="2.1", quote="Meals are reimbursable when the employee is traveling for work"):
    return {
        "choices": [
            {
                "message": {
                    "content": f'{{"category": "{category}", "confidence": {confidence}, "verdict": "{verdict}", "reasoning": "Looks good", "citations": [{{"section_id": "{section_id}", "quote": "{quote}"}}], "missing_info": []}}'
                }
            }
        ]
    }

def test_clean_claim():
    claim = ClaimIn(category="meals", description="Dinner while traveling to Bengaluru for client visit")
    
    with patch("httpx.post", mock_httpx_post(json_data=get_valid_json())):
        review = review_claim(claim)
    
    assert review.category == "meals"
    assert review.verdict == "complies"
    assert review.confidence >= 0.7
    assert review.uncertain is False
    assert review.citations[0].quote_verified is True

def test_ambiguous_claim():
    claim = ClaimIn(description="team thing at the pub")
    
    with patch("httpx.post", mock_httpx_post(json_data=get_valid_json(category="other", verdict="needs_clarification", confidence=0.8, quote="fake quote"))):
        review = review_claim(claim)
    
    assert review.category == "other"
    assert review.verdict == "needs_clarification"
    assert review.uncertain is True
    assert "AI could not map the claim to a specific policy category" in review.uncertain_reasons

def test_category_mismatch():
    claim = ClaimIn(category="meals", description="Dinner with client")
    
    with patch("httpx.post", mock_httpx_post(json_data=get_valid_json(category="client_entertainment", confidence=0.9))):
        review = review_claim(claim)
    
    assert review.uncertain is True
    assert "AI category 'client_entertainment' differs from claimed 'meals'" in review.uncertain_reasons

def test_low_confidence():
    claim = ClaimIn(category="meals", description="Dinner")
    
    with patch("httpx.post", mock_httpx_post(json_data=get_valid_json(confidence=0.6))):
        review = review_claim(claim)
    
    assert review.uncertain is True
    assert "confidence 0.6 is below 0.7" in review.uncertain_reasons

def test_citation_verification():
    claim = ClaimIn(category="meals", description="Dinner")
    
    json_data = {
        "choices": [
            {
                "message": {
                    "content": '{"category": "meals", "confidence": 0.9, "verdict": "complies", "reasoning": "ok", "citations": [{"section_id": "2.1", "quote": "Meals are reimbursable when the employee is traveling for work"}, {"section_id": "2.1", "quote": "Fabricated quote right here"}], "missing_info": []}'
                }
            }
        ]
    }
    with patch("httpx.post", mock_httpx_post(json_data=json_data)):
        review = review_claim(claim)
    
    assert review.citations[0].quote_verified is True
    assert review.citations[1].quote_verified is False

def test_ai_unavailable():
    claim = ClaimIn(category="meals", description="Dinner")
    
    with patch("httpx.post", mock_httpx_post(raise_exc=httpx.TimeoutException("timeout"))):
        with patch("time.sleep"):  # Skip sleep in tests
            with pytest.raises(AIServiceUnavailable):
                review_claim(claim)

def test_malformed_json():
    claim = ClaimIn(category="meals", description="Dinner")
    
    json_data_invalid = {
        "choices": [
            {
                "message": {
                    "content": '{ invalid json }'
                }
            }
        ]
    }
    
    mock = MagicMock()
    mock_resp_invalid = MagicMock()
    mock_resp_invalid.status_code = 200
    mock_resp_invalid.json.return_value = json_data_invalid
    
    mock_resp_valid = MagicMock()
    mock_resp_valid.status_code = 200
    mock_resp_valid.json.return_value = get_valid_json()
    
    mock.side_effect = [mock_resp_invalid, mock_resp_invalid, mock_resp_valid]
    
    with patch("httpx.post", mock):
        with patch("time.sleep"):
            review = review_claim(claim)
            
    assert review.category == "meals"

def test_pydantic_validation_failure():
    claim = ClaimIn(category="meals", description="Dinner")
    
    json_data_invalid = {
        "choices": [
            {
                "message": {
                    "content": '{"category": "meals", "confidence": 0.9, "reasoning": "ok", "citations": [], "missing_info": []}'
                }
            }
        ]
    }
    
    mock = MagicMock()
    mock_resp_invalid = MagicMock()
    mock_resp_invalid.status_code = 200
    mock_resp_invalid.json.return_value = json_data_invalid
    
    mock_resp_valid = MagicMock()
    mock_resp_valid.status_code = 200
    mock_resp_valid.json.return_value = get_valid_json()
    
    mock.side_effect = [mock_resp_invalid, mock_resp_valid]
    
    with patch("httpx.post", mock):
        with patch("time.sleep"):
            review = review_claim(claim)
            
    assert review.category == "meals"
