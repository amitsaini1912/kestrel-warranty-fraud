"""Train the final model on all decided claims, write predictions.csv and models/model.joblib.

Usage: python src/train.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, str(Path(__file__).parent))
from features import build, load_reference, load_test, load_train  # noqa: E402
from model import Calibrated, Ensemble, stack_inputs  # noqa: E402
import evaluate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA, MODELS = ROOT / "data", ROOT / "models"
HIST_COLS = ["claim_id", "submitted_at", "partner_id", "is_fraud", "claim_amount_inr",
             "partner_inspected"]


def main():
    partners, products = load_reference(DATA)
    tr, te = load_train(DATA), load_test(DATA)
    history = pd.concat([tr[HIST_COLS], te[HIST_COLS]], ignore_index=True)

    X = build(tr, history, partners, products)
    lab = X[X["is_fraud"].notna()].copy()
    w = (np.where(lab["label_noisy"], evaluate.LEGACY_WEIGHT, 1.0)
         * np.where(lab["post_policy"] == 1, evaluate.POST_WEIGHT, 1.0))
    ens = Ensemble().fit(lab, lab["is_fraud"].astype(int), w)

    # Calibrate on out-of-time backtest scores (never on the rows the model was fit on).
    bt_path = ROOT / "reports" / "backtest_rows.csv"
    if not bt_path.exists():
        evaluate.main()
    bt = pd.read_csv(bt_path)
    Z = stack_inputs(bt["score"].values, (bt["p_hist_fraud_90d"].values > 0).astype(float))
    cal = LogisticRegression(C=1.0).fit(Z, bt["is_fraud"].astype(int))
    print("stacker coefs (logit(raw), watchlist):", cal.coef_.round(3), cal.intercept_.round(3))
    model = Calibrated(ens, cal)

    Xt = build(te, history, partners, products)
    te_p = model.predict(Xt)
    sub = pd.DataFrame({"claim_id": te["claim_id"], "score": np.round(te_p, 6)})
    sample = pd.read_csv(DATA / "sample_submission.csv")
    sub = sample[["claim_id"]].merge(sub, on="claim_id", how="left")
    assert sub["score"].notna().all() and len(sub) == len(sample)
    sub.to_csv(ROOT / "predictions.csv", index=False)

    # Partner watchlist: confirmed fraud in the 90 days before the latest export (private file).
    lab_all = tr[tr["is_fraud"] == 1]
    cutoff = tr["submitted_at"].max() - pd.Timedelta(days=90)
    wl = (lab_all[lab_all["submitted_at"] >= cutoff].groupby("partner_id")
          .agg(confirmed_frauds_90d=("claim_id", "size"), fraud_rupees_90d=("claim_amount_inr", "sum"))
          .sort_values(["confirmed_frauds_90d", "fraud_rupees_90d"], ascending=False))
    (ROOT / "reports").mkdir(exist_ok=True)
    wl.to_csv(ROOT / "reports" / "watchlist.csv")
    print(f"watchlist: {len(wl)} partners -> reports/watchlist.csv")

    MODELS.mkdir(exist_ok=True)
    joblib.dump({"model": model, "history": history, "partners": partners,
                 "products": products}, MODELS / "model.joblib")
    print(f"predictions.csv: {len(sub)} rows, mean score {sub['score'].mean():.4f}, "
          f"top-120 mean {np.sort(te_p)[-120:].mean():.3f}")


if __name__ == "__main__":
    main()
