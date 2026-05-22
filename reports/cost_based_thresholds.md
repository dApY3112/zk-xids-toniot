# Cost-based Threshold Selection
Generated: 2026-02-12T20:39:14+00:00 (UTC)

## What this does
We choose decision thresholds by minimizing an explicit cost function on the validation set: `cost = C_FP * FP + C_FN * FN`, where FN/FP ratio is swept.

- Label 1 = Attack (positive), label 0 = Normal (negative)
- FP = Normal flagged as Attack (false alarm)
- FN = Attack missed (false negative)

## Ratios swept
- FN/FP ratios: 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0

## logistic_regression
- Figure: `reports/figures/cost_thresholds_logistic_regression.png`

Thresholds are tuned on validation; metrics/cost are reported on test.

| FN/FP | thr(val) | test FPR | test Recall | test MCC | test cost/sample |
|---:|---:|---:|---:|---:|---:|
| 0.25 | 0.089109 | 0.287680 | 0.994546 | 0.760713 | 0.011632 |
| 0.5 | 0.088104 | 0.288234 | 0.994600 | 0.761031 | 0.012941 |
| 1 | 0.088104 | 0.288234 | 0.994600 | 0.761031 | 0.015544 |
| 2 | 0.088104 | 0.288234 | 0.994600 | 0.761031 | 0.020751 |
| 5 | 0.004456 | 0.659622 | 0.999189 | 0.557664 | 0.027567 |
| 10 | 0.004456 | 0.659622 | 0.999189 | 0.557664 | 0.031477 |
| 20 | 0.000000 | 0.999001 | 1.000000 | 0.031028 | 0.035830 |
| 50 | 0.000000 | 0.999001 | 1.000000 | 0.031028 | 0.035830 |
| 100 | 0.000000 | 0.999001 | 1.000000 | 0.031028 | 0.035830 |

## xgboost
- Figure: `reports/figures/cost_thresholds_xgboost.png`

Thresholds are tuned on validation; metrics/cost are reported on test.

| FN/FP | thr(val) | test FPR | test Recall | test MCC | test cost/sample |
|---:|---:|---:|---:|---:|---:|
| 0.25 | 0.839778 | 0.007600 | 0.999071 | 0.983292 | 0.000496 |
| 0.5 | 0.714261 | 0.011649 | 0.999437 | 0.986130 | 0.000689 |
| 1 | 0.489287 | 0.015477 | 0.999639 | 0.986907 | 0.000903 |
| 2 | 0.356394 | 0.018861 | 0.999709 | 0.986105 | 0.001237 |
| 5 | 0.262545 | 0.021246 | 0.999757 | 0.985514 | 0.001936 |
| 10 | 0.090139 | 0.043213 | 0.999893 | 0.975843 | 0.002584 |
| 20 | 0.063064 | 0.051423 | 0.999917 | 0.971838 | 0.003436 |
| 50 | 0.019809 | 0.090531 | 0.999959 | 0.951455 | 0.005236 |
| 100 | 0.011841 | 0.119487 | 0.999963 | 0.935725 | 0.007867 |

