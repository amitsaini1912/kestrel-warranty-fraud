# Backtest (out-of-time, Jan-Jun 2026, retrained monthly)

Labelled claims scored: 4293; frauds: 67 (base rate 1.56%).

Scores below are for the shipped ranking (model score + partner watchlist).

ROC-AUC all months: 0.808 | May-Jun only: 0.774

PR-AUC all months: 0.469 | May-Jun only: 0.378 (random = base rate)

Accuracy of 'call everything genuine': 98.44% - the board's KPI is met by doing nothing.


## Investigation desk simulation (40 checks / month)

| strategy                         |   checked |   frauds |   fraud_total |   rupees_caught |   rupees_fraud_total |   genuine_held |     net |   rupees_per_check |   net_per_check |
|:---------------------------------|----------:|---------:|--------------:|----------------:|---------------------:|---------------:|--------:|-------------------:|----------------:|
| model + partner watchlist        |       240 |       43 |            67 |          177567 |               257845 |            197 |   40307 |                740 |             168 |
| model (probability-ranked)       |       240 |       30 |            67 |          160645 |               257845 |            210 |   18445 |                669 |              77 |
| model (rupee-ranked)             |       240 |       27 |            67 |          156788 |               257845 |            213 |   13448 |                653 |              56 |
| partner watchlist only           |       240 |       35 |            67 |          146566 |               257845 |            205 |    6266 |                611 |              26 |
| biggest claims first             |       240 |        9 |            67 |          130671 |               257845 |            231 |  -19509 |                544 |             -81 |
| random 40                        |       240 |       12 |            67 |           46986 |               257845 |            228 | -102054 |                196 |            -425 |
| new partners only (Ritu's hunch) |       240 |       12 |            67 |           18220 |               257845 |            228 | -130820 |                 76 |            -545 |


### May-June 2026 only (the regime the test period is in)

| strategy                         |   checked |   frauds |   fraud_total |   rupees_caught |   rupees_fraud_total |   genuine_held |    net |   rupees_per_check |
|:---------------------------------|----------:|---------:|--------------:|----------------:|---------------------:|---------------:|-------:|-------------------:|
| model + partner watchlist        |        80 |       23 |            36 |           34101 |                67123 |             57 |  -8359 |                426 |
| partner watchlist only           |        80 |       18 |            36 |           28302 |                67123 |             62 | -16058 |                354 |
| random 40                        |        80 |        6 |            36 |           24092 |                67123 |             74 | -24828 |                301 |
| new partners only (Ritu's hunch) |        80 |       12 |            36 |           18220 |                67123 |             68 | -28420 |                228 |
| model (probability-ranked)       |        80 |       10 |            36 |           17609 |                67123 |             70 | -29791 |                220 |
| biggest claims first             |        80 |        1 |            36 |           17866 |                67123 |             79 | -32954 |                223 |
| model (rupee-ranked)             |        80 |        8 |            36 |           14458 |                67123 |             72 | -33702 |                181 |


## Month by month (model, rupee-ranked)

| month   |   frauds |   fraud_total |   rupees_caught |   rupees_fraud_total |   genuine_held |    net |
|:--------|---------:|--------------:|----------------:|---------------------:|---------------:|-------:|
| 2026-01 |        5 |             8 |           33293 |                47614 |             35 |   9593 |
| 2026-02 |        5 |             5 |           49693 |                49693 |             35 |  25993 |
| 2026-03 |        6 |             9 |           42284 |                56429 |             34 |  18964 |
| 2026-04 |        3 |             9 |           17060 |                36986 |             37 |  -7400 |
| 2026-05 |        1 |            14 |            1995 |                21450 |             39 | -23225 |
| 2026-06 |        7 |            22 |           12463 |                45673 |             33 | -10477 |


Bootstrap 90% interval (model + watchlist), May-Jun fraud rupees caught per check: Rs 273 - Rs 557
