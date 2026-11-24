"""Data cleaning and feature building for the Kestrel warranty-claim fraud model.

All partner-history features are computed "as of" each claim's submission time,
using only claims submitted earlier, so training rows never see their own future.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

POLICY_CHANGE = pd.Timestamp("2026-05-01")   # §5: <Rs 2,000 auto-approved without inspection
AUTO_APPROVE_LIMIT = 2000.0
LABEL_LAG_DAYS = 7          # assume an investigation outcome is known ~1 week after submission
VELOCITY_WINDOW_DAYS = 30
SMOOTH_A = 20.0             # pseudo-count for smoothed partner fraud rate
GLOBAL_RATE = 0.0125

FEATURES = [
    "claim_amount_inr", "amount_to_list", "near_threshold", "under_limit", "post_policy",
    "inspected", "photo", "customer_prior_claims", "days_since_purchase", "warranty_used_frac",
    "partner_age_days", "partner_new", "ptype_franchise", "ptype_freelance", "ptype_asc",
    "serial_hyphen", "serial_lower", "serial_space", "note_blank",
    "p_hist_fraud", "p_hist_labeled", "p_hist_rate", "p_n_30d", "p_uninsp_small_30d",
    "p_velocity_ratio", "family_code", "auto_approved", "auto_approved_new",
    "p_hist_fraud_90d", "p_auto_share_30d",
]
FAMILIES = ["Air Fryer", "Ceiling Fan", "Induction Cooktop", "Mixer Grinder",
            "Robot Vacuum", "Room Heater", "Water Purifier"]


def load_reference(data_dir: Path):
    partners = pd.read_csv(data_dir / "partners.csv", parse_dates=["onboarded_date"])
    products = pd.read_csv(data_dir / "products.csv")
    return partners, products


def load_train(data_dir: Path) -> pd.DataFrame:
    """Clean the labelled export.

    * Re-submitted claims (same claim_id) -> keep the first submission only.
    * CRM rows with blank is_fraud are undecided -> label NaN (excluded from training).
    * legacy_zoho rows stored undecided as 0 -> label kept but flagged `label_noisy`.
    """
    tr = pd.read_csv(data_dir / "train.csv")
    tr["submitted_at"] = pd.to_datetime(tr["submitted_at"])
    tr = tr.sort_values("submitted_at").drop_duplicates("claim_id", keep="first")
    tr["label_noisy"] = (tr["source"] == "legacy_zoho") & (tr["is_fraud"] == 0)
    return tr.reset_index(drop=True)


def load_test(data_dir: Path) -> pd.DataFrame:
    te = pd.read_csv(data_dir / "test_unlabelled.csv")
    te["submitted_at"] = pd.to_datetime(te["submitted_at"])
    te["is_fraud"] = np.nan
    return te


def _serial_flags(s: pd.Series) -> pd.DataFrame:
    s = s.fillna("").astype(str)
    return pd.DataFrame({
        "serial_hyphen": s.str.contains("-").astype(int),
        "serial_lower": s.str.strip().str.match(r"^[a-z]").astype(int),
        "serial_space": (s != s.str.strip()).astype(int),
    }, index=s.index)


def static_features(df: pd.DataFrame, partners, products) -> pd.DataFrame:
    d = df.merge(partners, on="partner_id", how="left").merge(products, on="sku", how="left")
    amt = d["claim_amount_inr"].astype(float)
    d["amount_to_list"] = amt / d["list_price_inr"]
    d["under_limit"] = (amt < AUTO_APPROVE_LIMIT).astype(int)
    d["near_threshold"] = ((amt >= 1800) & (amt < AUTO_APPROVE_LIMIT)).astype(int)
    d["post_policy"] = (d["submitted_at"] >= POLICY_CHANGE).astype(int)
    d["inspected"] = (d["partner_inspected"] == "Y").astype(int)
    d["photo"] = (d["photo_attached"] == "Y").astype(int)
    d["warranty_used_frac"] = d["days_since_purchase"] / (d["warranty_months"] * 30.4)
    d["partner_age_days"] = (d["submitted_at"] - d["onboarded_date"]).dt.days
    d["partner_new"] = (d["partner_age_days"] < 365).astype(int)
    d["ptype_franchise"] = (d["partner_type"] == "franchise").astype(int)
    d["ptype_freelance"] = (d["partner_type"] == "freelance_technician").astype(int)
    d["ptype_asc"] = (d["partner_type"] == "authorised_service_centre").astype(int)
    d["note_blank"] = d["inspector_note"].isna().astype(int)
    d["auto_approved"] = ((d["post_policy"] == 1) & (d["under_limit"] == 1)
                          & (d["inspected"] == 0)).astype(int)
    d["auto_approved_new"] = d["auto_approved"] * d["partner_new"]
    d["family_code"] = d["family"].map({f: i for i, f in enumerate(FAMILIES)}).fillna(-1)
    d = pd.concat([d, _serial_flags(d["product_serial"])], axis=1)
    return d


def history_features(target: pd.DataFrame, history: pd.DataFrame) -> pd.DataFrame:
    """Partner history for each target row, using only `history` rows submitted before it.

    history: every known claim (labelled or not) with submitted_at, partner_id,
             is_fraud (NaN if unknown), claim_amount_inr, partner_inspected.
    """
    out = np.zeros((len(target), 8))
    h = history.sort_values("submitted_at")
    groups = {p: g for p, g in h.groupby("partner_id")}
    lag = pd.Timedelta(days=LABEL_LAG_DAYS)
    win = pd.Timedelta(days=VELOCITY_WINDOW_DAYS)
    for i, (pid, t) in enumerate(zip(target["partner_id"].values, target["submitted_at"].values)):
        g = groups.get(pid)
        if g is None:
            out[i] = [0, 0, GLOBAL_RATE, 0, 0, 1.0, 0, 0]
            continue
        ts = g["submitted_at"].values
        t = np.datetime64(t)
        lab = g[(ts < t - lag) & g["is_fraud"].notna().values]
        nf, nl = lab["is_fraud"].sum(), len(lab)
        rate = (nf + SMOOTH_A * GLOBAL_RATE) / (nl + SMOOTH_A)
        prev = g[ts < t]
        recent = prev[prev["submitted_at"].values >= t - win]
        n30 = len(recent)
        uninsp_small = ((recent["claim_amount_inr"] < AUTO_APPROVE_LIMIT)
                        & (recent["partner_inspected"] == "N")).sum()
        span_days = max((t - ts.min()) / np.timedelta64(1, "D"), 30.0) if len(prev) else 30.0
        base_30 = len(prev) / span_days * 30.0 if len(prev) else 0.0
        vel = (n30 + 1.0) / (base_30 + 1.0)
        nf90 = lab.loc[lab["submitted_at"].values >= t - np.timedelta64(90, "D"), "is_fraud"].sum()
        auto_share = uninsp_small / n30 if n30 else 0.0
        out[i] = [nf, nl, rate, n30, uninsp_small, vel, nf90, auto_share]
    cols = ["p_hist_fraud", "p_hist_labeled", "p_hist_rate", "p_n_30d",
            "p_uninsp_small_30d", "p_velocity_ratio", "p_hist_fraud_90d", "p_auto_share_30d"]
    return pd.DataFrame(out, columns=cols, index=target.index)


def build(target: pd.DataFrame, history: pd.DataFrame, partners, products) -> pd.DataFrame:
    d = static_features(target, partners, products)
    hf = history_features(d, history)
    return pd.concat([d, hf], axis=1)
