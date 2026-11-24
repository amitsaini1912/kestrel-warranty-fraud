"""Model definition, shared by training, evaluation and the API."""
from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from features import FEATURES

GOODWILL_PER_HELD_GENUINE = 380.0   # policy §4
REVIEW_COST = 260.0                 # policy §4, blended cost of a service contact
MONTHLY_CAPACITY = 40               # policy §5


def make_model(kind: str = "hgb", seed: int = 0):
    if kind == "hgb":
        return HistGradientBoostingClassifier(
            max_depth=3, learning_rate=0.05, max_iter=300, min_samples_leaf=40,
            l2_regularization=1.0, class_weight="balanced", random_state=seed)
    if kind == "logreg":
        return make_pipeline(StandardScaler(), LogisticRegression(
            C=0.3, class_weight="balanced", max_iter=2000))
    raise ValueError(kind)


class Ensemble:
    """Average of a few seeds of the boosted model + a logistic model (rank-stable)."""

    def __init__(self, seeds=(0, 1, 2)):
        self.models = [make_model("hgb", s) for s in seeds] + [make_model("logreg")]

    def fit(self, X, y, w=None):
        for m in self.models:
            if w is not None and not hasattr(m, "steps"):
                m.fit(X[FEATURES], y, sample_weight=w)
            elif w is not None:
                m.fit(X[FEATURES], y, logisticregression__sample_weight=w)
            else:
                m.fit(X[FEATURES], y)
        return self

    def raw(self, X):
        return np.mean([m.predict_proba(X[FEATURES])[:, 1] for m in self.models], axis=0)


def watchlisted(X):
    """Partner had a confirmed fraud in the last 90 days."""
    return (np.asarray(X["p_hist_fraud_90d"]) > 0).astype(float)


def stack_inputs(raw, watch):
    r = np.clip(raw, 1e-6, 1 - 1e-6)
    return np.column_stack([np.log(r / (1 - r)), watch])


class Calibrated:
    """Ensemble score + partner-watchlist flag, combined and calibrated by a small
    logistic layer fitted on OUT-OF-TIME backtest scores, so the output reads as a
    probability (class_weight='balanced' inflates raw scores)."""

    def __init__(self, ens: Ensemble, stacker):
        self.ens, self.stacker = ens, stacker

    def predict(self, X):
        return self.stacker.predict_proba(stack_inputs(self.ens.raw(X), watchlisted(X)))[:, 1]


def expected_saving(p, amount):
    """Rupees saved by reviewing this claim vs paying it blind (before review cost)."""
    return p * amount - (1 - p) * GOODWILL_PER_HELD_GENUINE
