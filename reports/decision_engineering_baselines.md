# Decision Engineering Evaluation (Baselines)
Generated: 2026-02-12T20:33:46+00:00 (UTC)
Data mode: `processed_stratified_sample_23files_frac0.15`
## Environment
- Python: `3.10.19`
- NumPy: `1.26.4`
- scikit-learn: `1.4.2`
- XGBoost: `3.1.2`
## Figures
All figures are under `reports/figures/`.
### xgboost
- ROC: `reports/figures/decision_engineering_xgboost_roc.png`
- PR: `reports/figures/decision_engineering_xgboost_pr.png`
- FPR vs Recall: `reports/figures/decision_engineering_xgboost_fpr_vs_recall.png`
- Reliability (raw): `reports/figures/decision_engineering_xgboost_reliability_raw.png`
- Reliability (Platt): `reports/figures/decision_engineering_xgboost_reliability_platt.png`
- Reliability (Isotonic): `reports/figures/decision_engineering_xgboost_reliability_isotonic.png`

#### Operating points (thresholds chosen on validation, evaluated on test)
Labels: `0=Normal`, `1=Attack`

| Point | Threshold | Attack Recall | Normal Recall (Spec) | FPR | MCC | Confusion (tn/fp/fn/tp) |
|---|---:|---:|---:|---:|---:|---|
| low_fpr | 0.807750 | 0.999226 | 0.991124 | 0.008876 | 0.984716 | 17867/160/375/484226 |
| balanced_mcc | 0.489287 | 0.999639 | 0.984523 | 0.015477 | 0.986907 | 17748/279/175/484426 |
| high_recall | 0.984017 | 0.994868 | 0.997615 | 0.002385 | 0.933712 | 17984/43/2487/482114 |

#### Calibration (test set)
| Variant | Brier | ECE |
|---|---:|---:|
| raw | 0.000732 | 0.000271 |
| platt | 0.000731 | 0.000174 |
| isotonic | 0.000732 | 0.000135 |

### logistic_regression
- ROC: `reports/figures/decision_engineering_logistic_regression_roc.png`
- PR: `reports/figures/decision_engineering_logistic_regression_pr.png`
- FPR vs Recall: `reports/figures/decision_engineering_logistic_regression_fpr_vs_recall.png`
- Reliability (raw): `reports/figures/decision_engineering_logistic_regression_reliability_raw.png`
- Reliability (Platt): `reports/figures/decision_engineering_logistic_regression_reliability_platt.png`
- Reliability (Isotonic): `reports/figures/decision_engineering_logistic_regression_reliability_isotonic.png`

#### Operating points (thresholds chosen on validation, evaluated on test)
Labels: `0=Normal`, `1=Attack`

| Point | Threshold | Attack Recall | Normal Recall (Spec) | FPR | MCC | Confusion (tn/fp/fn/tp) |
|---|---:|---:|---:|---:|---:|---|
| low_fpr | 0.938810 | 0.504396 | 0.990015 | 0.009985 | 0.183942 | 17847/180/240170/244431 |
| balanced_mcc | 0.088104 | 0.994600 | 0.711766 | 0.288234 | 0.761031 | 12831/5196/2617/481984 |
| high_recall | 0.081597 | 0.994903 | 0.681755 | 0.318245 | 0.745296 | 12290/5737/2470/482131 |

#### Calibration (test set)
| Variant | Brier | ECE |
|---|---:|---:|
| raw | 0.055734 | 0.121681 |
| platt | 0.016360 | 0.010188 |
| isotonic | 0.013126 | 0.000292 |

## Interpretation guide
- In this dataset, Normal is the minority class. So `FPR` and `Normal Recall (Specificity)` are critical for operational IDS value.
- Operating points make the imbalance problem explicit: you pick a threshold by cost constraints (false alarms vs missed attacks), not by default 0.5.
- Calibration complements classification quality: even with strong ROC/PR, probability estimates can be miscalibrated. ECE/Brier quantify this.
