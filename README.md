# Kestrel Home — warranty claim review

This tool ranks warranty claims for Kestrel's investigation desk, which can check 40 claims a month. For each claim it gives a fraud probability and a decision, and it explains the decision in plain language.

| File | What |
|---|---|
| `predictions.csv` | Score for every row of `test_unlabelled.csv` (higher = more likely fraud; calibrated probability) |
| `MEMO.md` | One-page memo to Ritu (non-technical) |
| `EVALUATION.md` | How I know it works, how often it fails, on which cases |
| `reports/backtest.md` | Full out-of-time backtest tables (generated) |
| `SUBMISSION_FORM.md` | My answers to the submission form |
| `src/` | `features.py` (cleaning + features), `model.py`, `evaluate.py` (backtest), `train.py` (final model + predictions) |
| `app/` | FastAPI service (`POST /score`) + one screen (`/`) |

## Run it (clean machine, Python 3.10+, no API keys needed)

```bash
git clone <this repo> && cd kestrel-fraud
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1. Put the data pack CSVs in data/ (not committed - see "Data" below):
#    train.csv test_unlabelled.csv partners.csv products.csv sample_submission.csv

python src/evaluate.py     # backtest -> reports/backtest.md   (~30 s)
python src/train.py        # final model -> models/model.joblib, predictions.csv, reports/watchlist.csv (~20 s)
uvicorn app.main:app --port 8000
# open http://localhost:8000  (screen)  or  http://localhost:8000/docs  (API)
python -m pytest -q tests  # smoke tests
```

If the model has not been trained yet, `/score` returns a 503 that tells you to run `python src/train.py`. Nothing in this project calls a paid API.

### API

`POST /score` with one claim. The fields are the same as the CSV, and `is_fraud` is not needed:

```bash
curl -X POST localhost:8000/score -H 'content-type: application/json' -d '{
  "submitted_at":"2026-07-14 11:05","partner_id":"SP3160","sku":"KH-AF-02",
  "days_since_purchase":60,"claim_amount_inr":1995,"photo_attached":"Y",
  "partner_inspected":"N","customer_prior_claims":1}'
```

It returns `fraud_probability`, a `decision` (send to desk / pay / pay but partner on watchlist), the `expected_rupees_saved_by_review`, and a list of `reasons`, for example "Partner has 10 confirmed frauds out of 39 investigated claims" or "Rs 1,995 sits just under the Rs 2,000 auto-approval line".

## Approach in brief
- **Cleaning.** Re-submitted claims are de-duplicated, keeping the first submission. Undecided CRM claims are dropped. Legacy-Zoho zeros, which may hide undecided cases, are down-weighted.
- **Features.** Amount vs list price; the auto-approval regime (under Rs 2,000, uninspected, after 1 May 2026); amounts just under the limit; inspection and photo; customer prior claims; partner age and type. There are also **partner history features** computed only from earlier claims: confirmed frauds, frauds in the last 90 days, uninspected small claims in the last 30 days, and volume spikes.
- **Model.** Three seeds of gradient-boosted trees plus logistic regression, averaged. A small logistic layer then combines that score with a "partner had a confirmed fraud in the last 90 days" flag. That layer is fitted on **out-of-time** backtest scores, so the output is a calibrated probability.
- **Evaluation.** Month-by-month out-of-time backtest that simulates the desk's 40 checks. It reports rupees, not accuracy. See `EVALUATION.md`.

## Decisions I made (no one to ask)
- **KPI.** Accuracy is reported but not optimised: flagging nothing scores 98.4%. The headline is fraud rupees stopped per check, which is Farhan's framing and matches the desk's 40-a-month capacity.
- **Ranking.** Claims are ranked by probability, not by expected rupees. Rupee-weighted ranking did worse out of time, because probability errors get multiplied by the amount.
- **Data (policy §10).** Raw CSVs, the trained model (which embeds partner histories), row-level backtest output and the partner watchlist are git-ignored. `predictions.csv` is committed because the brief requires it; it contains only claim IDs and scores.
- **Label lag.** I assumed an investigation outcome is known about 7 days after submission. The export has no resolution dates.
- **Submission form.** The cost question in the form mentions "Vireo, 650 tickets a week". That looks like a template leftover, so I answered for Kestrel's 750 claims a month.

## Known limitations
See `SUBMISSION_FORM.md` → "What is wrong with what you are handing us".
