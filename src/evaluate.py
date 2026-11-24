"""Out-of-time backtest: for each month Jan-Jun 2026, train on everything before it,
score that month, send the top-40 to the (simulated) investigation desk.

Writes reports/backtest.md and reports/backtest_rows.csv.
Usage: python src/evaluate.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).parent))
from features import build, load_reference, load_train  # noqa: E402
from model import (GOODWILL_PER_HELD_GENUINE, MONTHLY_CAPACITY, REVIEW_COST,  # noqa: E402
                   Ensemble, expected_saving)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
MONTHS = pd.period_range("2026-01", "2026-06", freq="M")
LEGACY_WEIGHT = 0.5    # legacy zeros contain undecided cases; trust them less
POST_WEIGHT = 3.0      # post-May rows describe the regime we will be scoring in


def desk(month_df: pd.DataFrame, priority: np.ndarray, k=MONTHLY_CAPACITY):
    idx = np.argsort(-priority)[:k]
    pick = month_df.iloc[idx]
    fraud = pick["is_fraud"] == 1
    caught = pick.loc[fraud, "claim_amount_inr"].sum()
    held = int((~fraud).sum())
    return dict(checked=len(pick), frauds=int(fraud.sum()),
                fraud_total=int((month_df["is_fraud"] == 1).sum()),
                rupees_caught=caught,
                rupees_fraud_total=month_df.loc[month_df["is_fraud"] == 1, "claim_amount_inr"].sum(),
                genuine_held=held,
                net=caught - held * GOODWILL_PER_HELD_GENUINE - len(pick) * REVIEW_COST)


def main():
    partners, products = load_reference(DATA)
    tr = load_train(DATA)
    X = build(tr, tr, partners, products)
    X["month"] = X["submitted_at"].dt.to_period("M")
    lab = X[X["is_fraud"].notna()].copy()
    lab["w"] = np.where(lab["label_noisy"], LEGACY_WEIGHT, 1.0) * np.where(lab["post_policy"] == 1, POST_WEIGHT, 1.0)

    rows, monthly = [], []
    rng = np.random.default_rng(0)
    for m in MONTHS:
        fit = lab[lab["month"] < m]
        ev = lab[lab["month"] == m].reset_index(drop=True)
        ens = Ensemble().fit(fit, fit["is_fraud"].astype(int), fit["w"].values)
        raw = ens.raw(ev)
        # calibrate on prior months' own out-of-time scores is costly; for ranking we only
        # need raw. Expected-value ranking uses a prior-month base rate rescale.
        base = fit["is_fraud"].mean()
        p = raw * base / max(raw.mean(), 1e-9)
        p = np.clip(p, 0, 1)
        strategies = {
            "model (rupee-ranked)": expected_saving(p, ev["claim_amount_inr"].values),
            "model (probability-ranked)": raw,
            "model + partner watchlist": raw + (ev["p_hist_fraud_90d"].values > 0),
            "partner watchlist only": (ev["p_hist_fraud_90d"].values > 0) + rng.random(len(ev)) * 1e-3,
            "new partners only (Ritu's hunch)": ev["partner_new"].values * 1.0 + rng.random(len(ev)) * 1e-3,
            "biggest claims first": ev["claim_amount_inr"].values,
            "random 40": rng.random(len(ev)),
        }
        for name, pr in strategies.items():
            r = desk(ev, pr); r.update(month=str(m), strategy=name); monthly.append(r)
        ev = ev.assign(score=raw, p=p)
        rows.append(ev[["claim_id", "month", "partner_id", "claim_amount_inr", "is_fraud",
                        "partner_new", "post_policy", "under_limit", "p_hist_fraud_90d", "score", "p"]])

    allrows = pd.concat(rows)
    REPORTS.mkdir(exist_ok=True)
    allrows.to_csv(REPORTS / "backtest_rows.csv", index=False)
    M = pd.DataFrame(monthly)

    allrows["final"] = allrows["score"] + (allrows["p_hist_fraud_90d"] > 0)
    y, s = allrows["is_fraud"].astype(int), allrows["final"]
    post = allrows["post_policy"] == 1
    lines = ["# Backtest (out-of-time, Jan-Jun 2026, retrained monthly)\n",
             f"Labelled claims scored: {len(allrows)}; frauds: {int(y.sum())} "
             f"(base rate {y.mean():.2%}).\n",
             "Scores below are for the shipped ranking (model score + partner watchlist).\n",
             f"ROC-AUC all months: {roc_auc_score(y, s):.3f} | May-Jun only: "
             f"{roc_auc_score(y[post], s[post]):.3f}\n",
             f"PR-AUC all months: {average_precision_score(y, s):.3f} | May-Jun only: "
             f"{average_precision_score(y[post], s[post]):.3f} (random = base rate)\n",
             f"Accuracy of 'call everything genuine': {(1 - y.mean()):.2%} - the board's KPI is met by doing nothing.\n",
             "\n## Investigation desk simulation (40 checks / month)\n"]
    agg = M.groupby("strategy")[["checked", "frauds", "fraud_total", "rupees_caught",
                                 "rupees_fraud_total", "genuine_held", "net"]].sum()
    agg["rupees_per_check"] = agg["rupees_caught"] / agg["checked"]
    agg["net_per_check"] = agg["net"] / agg["checked"]
    lines.append(agg.sort_values("net", ascending=False).round(0).to_markdown())
    lines.append("\n\n### May-June 2026 only (the regime the test period is in)\n")
    aggp = M[M["month"].isin(["2026-05", "2026-06"])].groupby("strategy")[
        ["checked", "frauds", "fraud_total", "rupees_caught", "rupees_fraud_total", "genuine_held", "net"]].sum()
    aggp["rupees_per_check"] = aggp["rupees_caught"] / aggp["checked"]
    lines.append(aggp.sort_values("net", ascending=False).round(0).to_markdown())
    lines.append("\n\n## Month by month (model, rupee-ranked)\n")
    lines.append(M[M["strategy"] == "model (rupee-ranked)"].set_index("month")[
        ["frauds", "fraud_total", "rupees_caught", "rupees_fraud_total", "genuine_held", "net"]].round(0).to_markdown())

    # bootstrap CI on the model's May-Jun rupees per check
    mm = allrows[post].reset_index(drop=True)
    boots = []
    for b in range(500):
        smp = mm.sample(len(mm), replace=True, random_state=b)
        tot = 0; chk = 0
        for _, g in smp.groupby("month"):
            g = g.reset_index(drop=True)
            r = desk(g, g["final"].values)
            tot += r["rupees_caught"]; chk += r["checked"]
        boots.append(tot / chk)
    lo, hi = np.percentile(boots, [5, 95])
    lines.append(f"\n\nBootstrap 90% interval (model + watchlist), May-Jun fraud rupees caught per check: Rs {lo:,.0f} - Rs {hi:,.0f}\n")
    (REPORTS / "backtest.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
