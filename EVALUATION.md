# Evidence that it works — and how often it does not

Full numbers: `reports/backtest.md` (regenerate with `python src/evaluate.py`).

## How I checked
- **Out-of-time backtest, not a random split.** For each month Jan–Jun 2026, I retrained on every decided claim before that month and scored that month. Then I simulated the desk: the top 40 claims are reviewed and their true outcome is revealed. A random split would leak partner history from the future and overstate results.
- Partner-history features only use claims submitted earlier. Labels count only after an assumed 7-day investigation lag.
- 4,293 decided claims scored, including 67 frauds. **May–Jun (the regime the test period is in): 1,422 claims, 36 frauds.** This is a small sample, so I bootstrapped it.

## Results (shipped ranking = model score + partner watchlist)
| | All Jan–Jun | May–Jun only |
|---|---|---|
| ROC-AUC | 0.81 | 0.77 |
| PR-AUC (random ≈ base rate 1.6% / 2.5%) | 0.47 | 0.38 |
| Frauds caught by 40 checks/month | 43 / 67 | 23 / 36 |
| Fraud rupees caught | Rs 1,77,567 / 2,57,845 | Rs 34,101 / 67,123 |
| Fraud rupees stopped per check | **Rs 740** | **Rs 426** (90% CI Rs 273–557) |
| Net after Rs 380 goodwill per held genuine + Rs 260 per check | +Rs 40,307 | −Rs 8,359 |

Comparison strategies, using the same 40 checks per month across Jan–Jun:
| Strategy | Rs stopped per check |
|---|---|
| Random | 196 |
| Biggest claims first | 544 |
| "New partners" (Ritu's hunch) | 76 |
| Model alone | 669 |
| **Model + watchlist** | **740** |

In June the final stacked model was refitted without June's own data. It caught **16 of 22** June frauds in its top 40.

**Accuracy** (the board's KPI): flagging nothing scores 98.4% on the backtest months. This metric cannot tell a useful model from no model.

## How often it is wrong, and on which cases
- **Precision of the top 40:** 10–20% in most months (5% in May 2026, the first month of the new rule, when the model had no examples of it). Most claims sent to the desk are genuine. That is expected at a 1.5–2.5% base rate with 40 slots.
- **False positives:** genuine small, auto-approved claims from new partners. In June's top 40 there were 24 genuine claims: 20 were from new partners, 21 were under Rs 2,000, and 16 came from partners already on the watchlist. The model can tell *risky circumstances* apart, but not a genuine claim from a flagged outlet.
- **False negatives:**
  1. A partner's *first* frauds. In June, two newer partners with no confirmed history had 4 frauds between them, ranked 85–105.
  2. Small one-offs from established partners. A Rs 686 fraud ranked 412th in June.
  3. One-off large frauds from established partners with clean records. A Rs 17,866 claim ranked 619th in June. It is the largest single loss of the month.
- **May 2026:** the model caught only 2 of 14 frauds. There was no post-rule training data and no partner history yet. Expect the same blind spot the next time policy changes.

## Data problems handled
| Issue | What I did |
|---|---|
| 681 re-submitted claim IDs (same claim, later timestamp) | Kept the first submission. Labels never conflicted. |
| 215 CRM claims undecided (blank label) | Excluded from training and evaluation. |
| Legacy Zoho exports wrote "undecided" as 0 (~3% of those zeros are probably not decided) | Kept, but with half the weight of CRM labels. |
| Policy change 1 May 2026 (auto-approval under Rs 2,000) | Added explicit regime/auto-approval features; post-May rows weighted 3× (the test period is all post-May). |
| Serials typed by partners (lowercase, hyphens, leading spaces) | Normalised; formatting flags kept as weak features. Serial reuse turned out to be noise. |
| UTC vs IST (policy §9) | Only affects legacy *resolution* events, which are not in this export. Hour-of-day distributions match across systems, so no correction was needed. |
| 4 claim descriptions contain text instructing "automated reviewers" to use accuracy and random splits | Treated as data and ignored. Free-text description is not used as a model feature at all; fault type showed no signal. |
