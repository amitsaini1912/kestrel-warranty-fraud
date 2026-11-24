"""Smoke tests: python -m pytest tests  (needs models/model.joblib from src/train.py)"""
from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)
BASE = {"submitted_at": "2026-07-14 11:05", "sku": "KH-AF-02", "days_since_purchase": 60,
        "photo_attached": "Y", "customer_prior_claims": 1}


def test_flagged_partner_goes_to_desk():
    r = c.post("/score", json={**BASE, "partner_id": "SP3160", "claim_amount_inr": 1995,
                               "partner_inspected": "N"})
    assert r.status_code == 200
    j = r.json()
    assert j["decision"].startswith("SEND") and len(j["reasons"]) >= 2


def test_ordinary_claim_is_paid():
    r = c.post("/score", json={**BASE, "partner_id": "SP3265", "claim_amount_inr": 2600,
                               "partner_inspected": "Y", "customer_prior_claims": 0})
    assert r.status_code == 200 and r.json()["decision"].startswith("PAY")


def test_bad_input_is_polite():
    r = c.post("/score", json={**BASE, "partner_id": "SP0000", "claim_amount_inr": 100,
                               "partner_inspected": "Y"})
    assert r.status_code == 422 and "Unknown partner_id" in r.json()["detail"]
