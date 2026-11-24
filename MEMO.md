# Memo — Warranty fraud: what to do next week

**To:** Ritu Deshpande, Head of D2C Operations · **Re:** Fraud flag on warranty claims

**The decision.** Don't sell the board an accuracy number. A model that approves every claim and flags nothing scores 98.4% accuracy on your own data, because only about 1.5 in 100 claims are fraud. So "above 97%" will look like success even when no fraud is stopped. Report two numbers instead: **fraud rupees stopped per claim checked**, and **fraud rupees paid out each month**.

**What the data says.**
- Fraud doubled after the 1 May rule that auto-approves claims under Rs 2,000 without inspection. It went from about 1.1% of claims to 2.5%.
- **It is a few outlets, not new partners in general.** 45 new partners filed claims since May. 37 of them had no confirmed fraud. Seven partners account for 33 of the 36 confirmed frauds since May (Rs 47,000 of Rs 67,000). Many of their claims sit just under the Rs 2,000 auto-approval line, at amounts like Rs 1,995. Meenal is right. Restricting all new partners would catch fewer frauds than random checks would, and it would hurt coverage in tier-2/3 cities.
- Before May, fraud was mostly one-off large claims close to the product's price. The tool still catches that pattern.

**The number.** I tested the tool on Jan–Jun 2026 as if it had been running then: each month it was retrained on earlier data only and picked the desk's 40 claims.
- Across the 6 months it caught **43 of 67 frauds (Rs 1.78 lakh of Rs 2.58 lakh)** at **Rs 740 of fraud stopped per claim checked**. The same 40 checks picked at random stop about Rs 200.
- In June alone, the latest month, it caught **16 of 22 frauds**.

**The rupees.** Total confirmed fraud is about **Rs 45,000 a month**. This is a real problem but not a large one. Even when the tool picks correctly, a desk check on a Rs 1,500 claim barely pays for itself: each genuine customer held costs Rs 380 in goodwill, and each check costs Rs 260. So the desk alone is not enough. The cheaper control is at the partner level.

**What to do next week.**
1. **Remove auto-approval for the 7 flagged partners.** Their claims would need inspection sign-off and a photo again. That is about 30 claims a month, about half of them fraud based on June. It would have prevented roughly **Rs 20,000+ of fraud a month** and affects about 12 genuine customers a month. The list is in the private file `reports/watchlist.csv`. It stays out of the public repo per policy §10.
2. **Give the desk the ranked list each week.** Review the top 10 claims each week (40 a month). Each flag comes with plain-language reasons the desk can check.
3. **Fix the data.** Close the undecided cases faster, and stop old Zoho exports turning "undecided" into "not fraud". Today the tool learns from both.
4. **Keep onboarding new partners.** Add a rule instead: if a partner's under-Rs-2,000 claims spike in their first 6 months, the partner gets reviewed automatically.

**Limits.** Fraud since May is about 36 confirmed cases, so every figure here has wide error bars. A fraudster's first claim cannot be spotted from partner history. The tool will miss it until the first confirmed fraud.
