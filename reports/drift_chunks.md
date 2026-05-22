# Drift / Robustness Check (Chunked Test)

Generated: 2026-02-12T20:36:36+00:00 (UTC)

Data mode: `processed_stratified_sample_23files_frac0.15`

## What this measures

We reorder the test split by ascending `test_idx` (proxy for original sample order), split into contiguous chunks, and track metric stability across chunks. Large drops suggest potential drift / non-stationarity.

## Environment

- Python: `3.10.19`
- NumPy: `1.26.4`
- scikit-learn: `1.4.2`
- XGBoost: `3.1.2`

## Figures

Figures are under `reports/figures/`.

- xgboost: `reports/figures/drift_chunks_xgboost.png`
- logistic_regression: `reports/figures/drift_chunks_logistic_regression.png`

## Summary statistics (test chunks)

Each metric is summarized across chunks (min/mean/max).

| Model | Variant | FPR min/mean/max | Recall min/mean/max | MCC min/mean/max |
|---|---|---|---|---|
| xgboost | default_0.5 | 0.000000/0.014920/0.082228 | 0.998745/0.999627/0.999920 | 0.836560/0.965167/0.996708 |
| xgboost | tuned_mcc | 0.000000/0.014937/0.082228 | 0.998745/0.999635/0.999920 | 0.836560/0.966291/0.996708 |
| logistic_regression | default_0.5 | 0.008000/0.119252/0.347480 | 0.838049/0.934987/0.998069 | 0.046015/0.491627/0.942405 |
| logistic_regression | tuned_mcc | 0.027027/0.377119/0.932584 | 0.959281/0.994229/0.999437 | 0.116723/0.600211/0.907167 |

## Notes

- This is a lightweight drift proxy; it does not require timestamps.
- If you later add time/file metadata, repeat the same evaluation grouped by file or time window.
