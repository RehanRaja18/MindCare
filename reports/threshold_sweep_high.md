# P(High)-Only Threshold Sweep — Tuned Random Forest, 3-Class Target

## Scope

- Model: tuned Random Forest (n_estimators=200, max_depth=10, min_samples_split=10, min_samples_leaf=4, max_features='sqrt', class_weight='balanced') from `reports/tuning_results_3class.json`.
- Evaluation: `X_val`/`y_val` from `mindcare_processed_splits_3class.npz`; test set untouched.
- Validation rows: 1650; seed: 42.
- Flag rule at each threshold t: flag row if P(High) >= t, **unconditional on predicted class** (isolates the P(High) component of the combined rule in `reports/uncertainty_flagging.md`).
- Known unanimous True-High/Predicted-Medium misses (baseline models): 17 rows.
- True High rows in validation set overall: 165.

## Threshold Sweep

| Threshold | Misses flagged (17) | Val rows flagged | Val flagged % | False-flag rate | True-High rows flagged |
|---:|---:|---:|---:|---:|---:|
| 0.05 | 15/17 (0.8824) | 672/1650 | 0.4073 | 0.8244 | 163/165 (0.9879) |
| 0.08 | 12/17 (0.7059) | 447/1650 | 0.2709 | 0.8904 | 160/165 (0.9697) |
| 0.10 | 9/17 (0.5294) | 346/1650 | 0.2097 | 0.9277 | 157/165 (0.9515) |
| 0.12 | 6/17 (0.3529) | 284/1650 | 0.1721 | 0.9472 | 154/165 (0.9333) |
| 0.15 | 4/17 (0.2353) | 231/1650 | 0.1400 | 0.9697 | 152/165 (0.9212) |
| 0.18 | 4/17 (0.2353) | 191/1650 | 0.1158 | 0.9686 | 152/165 (0.9212) |
| 0.20 | 3/17 (0.1765) | 181/1650 | 0.1097 | 0.9724 | 151/165 (0.9152) |
| 0.25 | 2/17 (0.1176) | 160/1650 | 0.0970 | 0.9812 | 150/165 (0.9091) |

## Interpretation

Prototype-model metrics on a very likely synthetic dataset (see CLAUDE.md); not clinical validation. False-flag rate here is the fraction of ALL flagged rows (any true class) that the tuned Random Forest already classified correctly — i.e. review workload spent on cases where flagging doesn't change the outcome.
