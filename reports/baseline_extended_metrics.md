# Baseline Metrics (Imbalance-Aware)

Generated: 2026-02-12T20:33:38+00:00 (UTC)

Data mode: `processed_stratified_sample_23files_frac0.15`

## Environment

- Python: `3.10.19`

- NumPy: `1.26.4`

- scikit-learn: `1.4.2`

- XGBoost: `3.1.2`

## Why this file exists

The TON_IoT processed network dataset is severely imbalanced: Attack is the majority class and Normal is the minority class. Therefore, accuracy (and Attack-positive PR-AUC) can look overly optimistic. This report adds Normal-side metrics (specificity/FPR) and threshold tuning on the validation set.

## Key metrics (test set)

Labels: `0 = Normal`, `1 = Attack`



| Model | Threshold | Balanced Acc | MCC | Attack Recall | Normal Recall (Specificity) | FPR | PR-AUC (Attack) | PR-AUC (Normal) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| xgboost (default@0.5) | 0.500000 | 0.992132 | 0.986851 | 0.999631 | 0.984634 | 0.015366 | 0.999997 | 0.998401 |
| xgboost (tuned@MCC) | 0.489287 | 0.992081 | 0.986907 | 0.999639 | 0.984523 | 0.015477 | 0.999997 | 0.998401 |
| xgboost (tuned@BAcc) | 0.968393 | 0.996811 | 0.955497 | 0.996729 | 0.996894 | 0.003106 | 0.999997 | 0.998401 |
| logistic_regression (default@0.5) | 0.500000 | 0.923103 | 0.535818 | 0.935017 | 0.911189 | 0.088811 | 0.998669 | 0.726311 |
| logistic_regression (tuned@MCC) | 0.088104 | 0.853183 | 0.761031 | 0.994600 | 0.711766 | 0.288234 | 0.998669 | 0.726311 |
| logistic_regression (tuned@BAcc) | 0.620204 | 0.929770 | 0.538253 | 0.933095 | 0.926444 | 0.073556 | 0.998669 | 0.726311 |


## Notes

- `tuned@MCC` and `tuned@BAcc` select thresholds on the validation set that maximize MCC or Balanced Accuracy, respectively.

- Use `Normal Recall (Specificity)` + `FPR` to reason about false alarms, because Normal is the minority class here.

- If you see warnings about unpickling model objects from a different library version, regenerate `outputs/models/*.pkl` by re-running `notebooks/04_train_and_evaluate_baseline.ipynb` under the pinned environment (recommended for strict reproducibility).
