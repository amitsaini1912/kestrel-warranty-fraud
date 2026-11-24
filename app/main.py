"""Claim-scoring service.  Run:  uvicorn app.main:app --port 8000"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from features import AUTO_APPROVE_LIMIT, build  # noqa: E402
from model import GOODWILL_PER_HELD_GENUINE, REVIEW_COST, expected_saving  # noqa: E402

MODEL_PATH = ROOT / "models" / "model.joblib"
REVIEW_THRESHOLD = 0.09   # = score of the ~40th highest claim per month on Jul-Sep 2026 (desk capacity)

app = FastAPI(title="Kestrel warranty-claim review")
_state: dict = {}


def _load():
    if "model" not in _state:
        if not MODEL_PATH.exists():
            raise HTTPException(503, "Model not trained yet. Run: python src/train.py")
        _state.update(joblib.load(MODEL_PATH))
    return _state


class Claim(BaseModel):
    claim_id: str = "NEW"
    submitted_at: str = Field(..., examples=["2026-07-14 11:05"])
    partner_id: str = Field(..., examples=["SP3160"])
    sku: str = Field(..., examples=["KH-AF-02"])
    product_serial: str = ""
    days_since_purchase: int
    claim_amount_inr: float
    photo_attached: Literal["Y", "N"]
    partner_inspected: Literal["Y", "N"]
    claim_description: str = ""
    inspector_note: Optional[str] = None
    customer_prior_claims: int = 0
    source: str = "crm"


def _reasons(r: pd.Series, partners) -> list[str]:
    out = []
    if r["p_hist_fraud"] > 0:
        out.append(f"Partner {r['partner_id']} has {int(r['p_hist_fraud'])} confirmed fraud(s) out of "
                   f"{int(r['p_hist_labeled'])} investigated claims ({int(r['p_hist_fraud_90d'])} in the last 90 days).")
    if r["auto_approved"]:
        months = int(r["partner_age_days"] // 30)
        out.append(f"Auto-approved without inspection (under Rs 2,000, after the May 2026 rule); "
                   f"partner onboarded {months} month(s) ago.")
    if r["near_threshold"]:
        out.append(f"Amount Rs {r['claim_amount_inr']:,.0f} sits just under the Rs 2,000 auto-approval line.")
    if r["amount_to_list"] >= 0.6:
        out.append(f"Claim is {r['amount_to_list']:.0%} of the product's list price.")
    if r["customer_prior_claims"] >= 2:
        out.append(f"Customer already has {int(r['customer_prior_claims'])} earlier warranty claims.")
    if r["p_uninsp_small_30d"] >= 3:
        out.append(f"Partner filed {int(r['p_uninsp_small_30d'])} uninspected small claims in the last 30 days.")
    if r["claim_amount_inr"] >= AUTO_APPROVE_LIMIT and r["inspected"] == 0:
        out.append("Large claim with no inspection sign-off (policy requires one).")
    if not out:
        out.append("No specific risk pattern found; score reflects the general base rate.")
    return out


@app.get("/health")
def health():
    return {"ok": True, "model_loaded": MODEL_PATH.exists()}


@app.post("/score")
def score(claim: Claim):
    s = _load()
    rec = pd.DataFrame([claim.model_dump()])
    try:
        rec["submitted_at"] = pd.to_datetime(rec["submitted_at"])
    except Exception:
        raise HTTPException(422, "submitted_at must look like 2026-07-14 11:05")
    if claim.partner_id not in set(s["partners"]["partner_id"]):
        raise HTTPException(422, f"Unknown partner_id {claim.partner_id}")
    if claim.sku not in set(s["products"]["sku"]):
        raise HTTPException(422, f"Unknown sku {claim.sku}")
    rec["is_fraud"] = float("nan")
    hist = s["history"][s["history"]["claim_id"] != claim.claim_id]
    X = build(rec, hist, s["partners"], s["products"])
    p = float(s["model"].predict(X)[0])
    saving = float(expected_saving(p, claim.claim_amount_inr))
    reasons = _reasons(X.iloc[0], s["partners"])
    if p < 0.05 and not reasons[0].startswith("No specific"):
        reasons = ["Low risk overall. Noted, but not enough on its own:"] + reasons
    watch = X.iloc[0]["p_hist_fraud_90d"] > 0
    if p >= REVIEW_THRESHOLD and saving > 0:
        decision = "SEND TO INVESTIGATION DESK"
    elif watch:
        decision = "PAY, BUT PARTNER IS ON WATCHLIST - require inspection sign-off and photo"
    else:
        decision = "PAY (no review)"
    return {
        "claim_id": claim.claim_id,
        "fraud_probability": round(p, 4),
        "decision": decision,
        "expected_rupees_saved_by_review": round(saving - REVIEW_COST, 0),
        "reasons": reasons,
        "note": (f"Holding a genuine claim costs ~Rs {GOODWILL_PER_HELD_GENUINE:.0f} goodwill; "
                 f"a review costs ~Rs {REVIEW_COST:.0f}. Desk capacity is 40 claims/month."),
    }


@app.get("/")
def index():
    return FileResponse(ROOT / "app" / "static" / "index.html")
