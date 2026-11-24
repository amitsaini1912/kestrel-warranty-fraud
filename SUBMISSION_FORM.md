# Submission form answers

Paste each answer into the matching form field.

---

### What did you build, and what business outcome does it move? State the number and the money.
I built a claim-ranking model and service for Kestrel's investigation desk, which can check 40 claims a month. For each claim it gives a fraud probability, a decision and plain-language reasons. I also found where the fraud actually comes from.

- **The number:** **Rs 740 of fraud stopped per claim checked.** This comes from an out-of-time backtest over Jan–Jun 2026, retrained monthly. Picking the 40 claims at random stops about Rs 196 per check.
- **The money:** over those 6 months the tool caught 43 of 67 frauds, worth Rs 1.78 lakh of Rs 2.58 lakh. That is +Rs 40k net after Rs 380 goodwill for each genuine claim held and Rs 260 per check.
- **The finding:** since the 1 May auto-approval rule, 7 partners account for 33 of 36 confirmed frauds (Rs 47k of Rs 67k). It is not new partners in general: 37 of 45 active new partners had zero fraud. Removing auto-approval for those 7 partners would have stopped roughly Rs 20k a month. In June, using a watchlist built from May only, their 32 claims contained 16 of June's 22 frauds.
- **Accuracy:** flagging nothing scores 98.4% on this data. It meets the board's ">97%" target without stopping any fraud.

### What does one run cost, and what would a month cost at Vireo's volume (roughly 650 tickets a week)? Show the arithmetic. If you used no paid calls, say so.
**No paid calls.** The model is scikit-learn running locally, with no LLM or API in the product. This question names "Vireo" and tickets, which looks like a leftover from another brief, so I answered for Kestrel.

- One prediction takes about 40 ms of CPU, so the marginal cost is Rs 0.
- At 650 tickets a week (about 2,800 a month): 2,800 × 0.04 s ≈ 2 CPU-minutes a month. That costs Rs 0 at the margin. A small always-on VM (1 vCPU) runs about Rs 500–1,000 a month if it needs hosting.
- Retraining takes about 50 s of CPU (backtest plus final fit), roughly Rs 0.

### What does one prediction cost, and what would a month cost at Kestrel's volume (about 750 warranty claims a month)?
**No paid calls.** 750 claims × about 40 ms ≈ 30 CPU-seconds a month, so about Rs 0 marginal. Infrastructure is at most a small VM, about Rs 500–1,000 a month, or it can run on an existing server. Monthly retraining takes about 1 CPU-minute.

### How do you know it works? Sample size, how you checked, error rate, and the kind of case it gets wrong.
- **Method:** an out-of-time backtest. For each month Jan–Jun 2026, I trained only on earlier months and simulated the desk taking the top 40 claims. Partner-history features only use claims submitted earlier, with a 7-day label lag. There was no random split, because that leaks partner history from the future.
- **Sample:** 4,293 decided claims including 67 frauds. Of these, May–Jun (the current regime) is 1,422 claims with 36 frauds, which is small, so I bootstrapped it.
- **Results:** ROC-AUC 0.81 overall and 0.77 for May–Jun. PR-AUC is 0.47 against a base rate of 0.016. Fraud stopped per check is Rs 740 overall and Rs 426 for May–Jun (90% CI Rs 273–557). In June it caught 16 of 22 frauds in its top 40.
- **Error rate:** precision of the 40 checks is 10–20% in most months, so 32–36 of every 40 checked claims are genuine. That is expected with 1.5–2.5% fraud and 40 slots. Recall is about 64% (43 of 67).
- **What it gets wrong:**
  1. A partner's first frauds, before any are confirmed. In June, 4 such frauds ranked 85–105.
  2. One-off frauds from established clean partners, for example a Rs 17,866 claim ranked 619th.
  3. Policy changes. In May 2026 it caught only 2 of 14, because it had no data on the new rule yet.
  4. False positives, which are mostly genuine small auto-approved claims from flagged or new outlets.

### Did you change, narrow, or push back on the client's ask?
- **I pushed back on the KPI.** I report accuracy but do not optimise it: flagging nothing scores 98.4%. I replaced it with Farhan's measure, fraud rupees stopped per check, plus fraud rupees paid out per month. This is the opening line of the memo, because the board's KPI can be met while stopping nothing.
- **I narrowed Ritu's hypothesis.** "New partners are the problem" is true only for a handful of outlets. A blanket new-partner rule scores Rs 76 per check, worse than random. I recommend a partner-level control for 7 named partners instead, and protecting the rest, as Meenal asked.
- **I widened the scope beyond "flag claims".** Desk review of Rs 1,500 claims barely breaks even, because Rs 380 goodwill plus Rs 260 per check eats most of what a correct flag saves. So the bigger lever is a policy change: remove auto-approval for watchlisted partners.
- **I did not ship "live soon" as an auto-block.** The tool ranks claims for humans; it does not reject them.

### What is wrong with what you are handing us?
- **Small sample in the current regime** (36 post-May frauds), so every May–Jun figure has wide error bars.
- **Label noise:** legacy Zoho zeros contain some undecided cases. I down-weighted them (0.5) instead of fixing them, because I could not tell them apart.
- **Assumed 7-day investigation lag:** the export has no resolution dates. If investigations take longer, partner-history features are optimistic in the backtest.
- **Partner history is a snapshot:** the service uses history up to the export (30 Sep 2026). In production it must be refreshed as investigations close. There is no pipeline for that yet; you rerun `train.py`.
- **Calibration is fitted on only 67 frauds** from the backtest, so the probabilities are approximate. The ranking is more reliable than the exact percentages.
- **The watchlist effect is partly hindsight:** the "7 partners = 33 of 36" figure uses the same months the list came from. The honest forward test, building the list in May and testing on June, is 16 of 22.
- **The screen is minimal:** one claim at a time, no batch upload, no authentication.
- **Threshold:** the "send to desk" cut-off of 0.09 is set so about 40 claims a month pass on Jul–Sep volumes. It should be re-set monthly.

### What did you deliberately leave out, and why that rather than something else?
- **An LLM in the product, for example for reading descriptions or writing explanations.** Fault descriptions showed no signal, and 4 of them contain injected instructions aimed at automated reviewers. Rule-based reasons are free, deterministic and auditable. An LLM would add cost and an attack surface for no gain.
- **Heavier models and hyperparameter search** (XGBoost, deep nets, Optuna). With 36 frauds in the current regime, tuning overfits; better partner features gained far more.
- **Serial-number fraud checks.** Serial reuse turned out to be noise in this data; reused serials have the same fraud rate as unique ones.
- **Raw data, trained model and watchlist in the public repo.** Policy §10 forbids publishing operational data.
- **Auto-rejecting claims.** Goodwill cost and low precision make a human in the loop the right call.

### Anything you built or found that nobody asked for?
- **The partner watchlist** (`reports/watchlist.csv`, private), and the finding that 7 partners account for 33 of 36 post-May frauds. Many of their claims sit just under the auto-approval line, at amounts like Rs 1,995.
- **An economics check:** at Rs 380 goodwill plus Rs 260 per check, a desk check only pays for itself on a Rs 1,500 claim when there is more than about 34% chance it is fraud. That is why I recommend a partner-level control rather than only more desk checks.
- **Injected instructions in the data:** 4 claim descriptions contain text telling "automated reviewers" to use accuracy, random splits and new-partner flags. I treated them as data, ignored them, and do not use description text as a feature.
- **Data issues:** 681 duplicate resubmissions, Zoho's "undecided becomes 0" problem, and the UTC note in policy §9, which does not affect this export because it has no resolution events.

### What did you use AI for? Which tools and models, where they helped, where they wasted your time, what you threw away.
- **Tool:** Claude (Anthropic, Claude Opus model in the Claude app's agent mode), on a personal subscription, with no API spend.
- **Helped with:** fast EDA, writing the feature/backtest/service code, finding the post-May partner pattern, and first drafts of the memo and docs. I reviewed and edited everything.
- **Thrown away:**
  1. Ranking by expected rupees (probability × amount), which was worse out of time.
  2. A probability-only ranking without the partner watchlist, which caught 10 of 36 post-May frauds against 23 with it.
  3. A first calibration that rescaled to the base rate.
  4. An early reason list that showed risk factors even on low-risk claims, which confused the screen.
- **Wasted time:** a first model trained without regime features scored well before May but failed after it. It took a backtest split by month to see that.
- **Screen recording:** `<PASTE PUBLIC GOOGLE DRIVE LINK>`

### Someone picks this up on Monday and you are unreachable. The three things they need to know.
1. **Run `python src/evaluate.py` then `python src/train.py` every month after new investigation outcomes land.** This refreshes the partner history, the watchlist and the threshold. The model is only as good as the latest confirmed frauds.
2. **Judge it by rupees stopped per check and by `reports/backtest.md`, never by accuracy.** Flagging nothing scores 98%.
3. **The biggest win is not the model.** Get Ops to remove auto-approval for the partners in `reports/watchlist.csv` with 2 or more frauds. Watch for the next policy change: the model was blind for the first month after the last one.

### Honest hours spent.
`<FILL IN>`

### Github Repo Link
`<PASTE PUBLIC REPO URL>`
