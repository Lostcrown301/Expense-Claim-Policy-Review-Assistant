import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os

from app.main import app
from app.database import Base, get_db
from app.ai_service import AIServiceUnavailable
from unittest.mock import patch, MagicMock

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def mock_review_claim(*args, **kwargs):
    review = MagicMock()
    review.category = "meals"
    review.confidence = 0.9
    review.verdict = "complies"
    review.reasoning = "OK"
    review.citations = []
    review.missing_info = []
    review.uncertain = False
    review.uncertain_reasons = []
    return review

def mock_review_claim_unavailable(*args, **kwargs):
    raise AIServiceUnavailable("AI is down")

@patch("app.main.review_claim", side_effect=mock_review_claim)
def test_create_claim(mock_rc):
    response = client.post(
        "/claims",
        json={
            "claimant": "John Doe",
            "description": "Lunch with client",
            "category": "meals",
            "amount": 50,
            "currency": "INR",
            "date": "2026-10-06"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["claim"]["description"] == "Lunch with client"
    assert data["ai_review"]["verdict"] == "complies"
    assert data["validation"]["passed"] is True
    assert data["ai_status"] == "ok"

@patch("app.main.review_claim", side_effect=mock_review_claim_unavailable)
def test_create_claim_ai_unavailable(mock_rc):
    response = client.post(
        "/claims",
        json={
            "claimant": "John Doe",
            "description": "Lunch with client 2",
            "category": "meals",
            "amount": 60,
            "currency": "INR",
            "date": "2026-10-06"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["claim"]["description"] == "Lunch with client 2"
    assert data["ai_review"] is None
    assert data["validation"]["passed"] is True
    assert data["ai_status"] == "unavailable"

def test_get_claims():
    response = client.get("/claims")
    assert response.status_code == 200
    assert len(response.json()) >= 2

def test_get_claim_detail():
    response = client.get("/claims/1")
    assert response.status_code == 200
    data = response.json()
    assert data["claim"]["id"] == 1

def test_get_claim_not_found():
    response = client.get("/claims/9999")
    assert response.status_code == 404

def test_create_decision():
    response = client.post(
        "/claims/1/decision",
        json={
            "action": "approve",
            "reason": "Looks good"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "approve"
    assert data["reason"] == "Looks good"

def test_invalid_decision():
    response = client.post(
        "/claims/1/decision",
        json={
            "action": "request_clarification"
        }
    )
    assert response.status_code == 422

def test_category_override():
    response = client.post(
        "/claims/1/decision",
        json={
            "action": "override_category",
            "category": "travel_local",
            "reason": "Reviewer changed"
        }
    )
    assert response.status_code == 200
    
    response2 = client.post(
        "/claims/1/decision",
        json={
            "action": "override_category",
            "reason": "Reviewer changed"
        }
    )
    assert response2.status_code == 422
    
def test_decision_history():
    response = client.get("/claims/1/history")
    assert response.status_code == 200
    data = response.json()
    assert len(data["history"]) >= 2
