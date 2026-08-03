# Thesis ECDF Generation Report

Started: 2026-06-14T11:49:19+00:00 (UTC)
Finished: 2026-06-14T11:49:52+00:00 (UTC)
Elapsed time: 33.09 seconds
Peak process RSS: 480.10 MiB
Peak traced Python allocation: 401.59 MiB

## Files Inspected

- `tools/analyze_exact_shap_ranking_margin.py`
- `outputs/reports/exact_shap_ranking_margin.json`
- `outputs/reports/exact_shap_ranking_margin_examples.csv`
- `tools/eval_float_quantized_lr_agreement.py`
- `outputs/reports/float_vs_quantized_lr_agreement.json`
- `outputs/reports/float_vs_quantized_lr_examples.csv`
- `outputs/models/logreg_baseline.pkl`
- `outputs/processed/X_val.npy`
- `outputs/processed/X_test.npy`
- `outputs/processed/y_val.npy`
- `outputs/processed/y_test.npy`
- `stage3_zk/artifacts/model_public.json`
- `stage3_zk/artifacts/group_map.json`
- `stage3_zk/artifacts/exact_shap_reference.json`

## Scripts And Functions Reused

- `tools/analyze_exact_shap_ranking_margin.py`: reused `_chunks` and `_ordered_group_ids`.
- `tools/eval_float_quantized_lr_agreement.py`: reused `_load_pickle` and `_split_path`.
- The new script preserves the same quantized LR, Exact SHAP, rounding, scaling, and ranking conventions as the existing reports.

## Mathematical Definitions

- Exact SHAP group value: `phi_g_int = sum_{i in group g} w_int[i] * (x_int[i] - x_ref_int[i])`.
- Rank-3/rank-4 margin: `margin_scaled = (abs_phi_rank3_int - abs_phi_rank4_int) / (Sx * Sw)`.
- Float LR score: `float_score = X @ w_float + b_float`.
- Quantized LR score: `quant_score_scaled = (x_int @ w_int + b_int) / (Sx * Sw)`.
- Signed score error: `quant_score_scaled - float_score`.
- Absolute score error: `abs(quant_score_scaled - float_score)`.
- Prediction mismatch: `(float_score >= 0) != (quant_score_int >= 0)`.

## Input Artifacts And Sample Counts

- `val` Exact SHAP margins: 502628 samples.
- `val` LR score errors: 502628 samples.
- `test` Exact SHAP margins: 502628 samples.
- `test` LR score errors: 502628 samples.

## Runtime Environment

- Python: `3.12.3`
- Platform: `Windows-11-10.0.26200-SP0`
- NumPy: `1.26.4`
- Matplotlib: `3.9.2`
- Joblib: `1.4.2`
- scikit-learn: `1.5.1`
- Git revision: `586b51b`

## Execution Commands

```text
python -B tools/generate_thesis_distribution_ecdfs.py
```

## Validation Against Existing Thesis Values

Overall validation status: `PASS`

| Check | Actual | Expected | Deviation | Tolerance | Status |
|---|---:|---:|---:|---:|---|
| `shap.val.sample_count` | 502628 | 502628 | 0 | 0 | PASS |
| `shap.val.minimum` | 1.27404928207e-06 | 1e-06 | 2.74049282074e-07 | 5e-07 | PASS |
| `shap.val.p5` | 0.00041101500392 | 0.000411 | 1.50039196014e-08 | 5e-07 | PASS |
| `shap.val.median` | 0.0440134219825 | 0.044013 | 4.21982526783e-07 | 5e-07 | PASS |
| `shap.val.margin_le_0.001_percent` | 11.1722785042 | 11.172279 | -4.9581798045e-07 | 1e-05 | PASS |
| `shap.val.margin_le_0.01_percent` | 26.7951646148 | 26.8 | -0.00483538521531 | 0.01 | PASS |
| `shap.test.sample_count` | 502628 | 502628 | 0 | 0 | PASS |
| `shap.test.minimum` | 1.27404928207e-06 | 1e-06 | 2.74049282074e-07 | 5e-07 | PASS |
| `shap.test.p5` | 0.00041101500392 | 0.000411 | 1.50039196014e-08 | 5e-07 | PASS |
| `shap.test.median` | 0.0440134219825 | 0.044013 | 4.21982526783e-07 | 5e-07 | PASS |
| `shap.test.margin_le_0.001_percent` | 11.080162665 | 11.080163 | -3.3496741203e-07 | 1e-05 | PASS |
| `shap.test.margin_le_0.01_percent` | 26.8112799128 | 26.81 | 0.00127991277844 | 0.01 | PASS |
| `lr.val.sample_count` | 502628 | 502628 | 0 | 0 | PASS |
| `lr.val.prediction_agreement_percent` | 99.991246011 | 99.991246 | 1.09663602643e-08 | 1e-05 | PASS |
| `lr.val.prediction_mismatches` | 44 | 44 | 0 | 0 | PASS |
| `lr.val.mean_absolute_error` | 0.0409458800228 | 0.040946 | -1.1997717958e-07 | 1e-06 | PASS |
| `lr.val.p95` | 0.116889225871 | 0.116889 | 2.25871221907e-07 | 1e-06 | PASS |
| `lr.val.maximum_absolute_error` | 161.208082441 | 161.208082 | 4.41087763647e-07 | 1e-05 | PASS |
| `lr.test.sample_count` | 502628 | 502628 | 0 | 0 | PASS |
| `lr.test.prediction_agreement_percent` | 99.9942303254 | 99.99423 | 3.2540964412e-07 | 1e-05 | PASS |
| `lr.test.prediction_mismatches` | 29 | 29 | 0 | 0 | PASS |
| `lr.test.mean_absolute_error` | 0.0412967894188 | 0.041297 | -2.10581207076e-07 | 1e-06 | PASS |
| `lr.test.p95` | 0.116912564379 | 0.116913 | -4.35621259162e-07 | 1e-06 | PASS |
| `lr.test.maximum_absolute_error` | 154.911021538 | 154.911022 | -4.61733861812e-07 | 1e-05 | PASS |

## Exact Deviations From Existing Reports

All validation deviations are listed in the table above. All checks passed within the stated formatting tolerances.

## Output File Paths

- `outputs/thesis_extra/exact_shap_rank34_margins.npz`
- `outputs/thesis_extra/float_quantized_lr_score_errors.npz`
- `reports/thesis_extra/exact_shap_rank34_margin_ecdf_summary.json`
- `reports/thesis_extra/float_quantized_lr_error_ecdf_summary.json`
- `reports/thesis_extra/exact_shap_rank34_margin_percentiles.csv`
- `reports/thesis_extra/float_quantized_lr_error_percentiles.csv`
- `reports/figures/thesis_extra/exact_shap_rank34_margin_ecdf.png`
- `reports/figures/thesis_extra/exact_shap_rank34_margin_ecdf.svg`
- `reports/figures/thesis_extra/float_quantized_lr_absolute_error_ecdf.png`
- `reports/figures/thesis_extra/float_quantized_lr_absolute_error_ecdf.svg`
- `THESIS_ECDF_GENERATION_REPORT.md`

## Figure Captions

Figure X. Empirical cumulative distribution of the Stage 3.4 quantized Exact SHAP margin between the third- and fourth-ranked semantic groups. The validation and test splits each contain 502,628 samples. Margins at or below 0.001 occur in 11.1723% of validation samples and 11.0802% of test samples; margins at or below 0.01 occur in 26.7952% and 26.8113% respectively. No zero values were present; a logarithmic x-axis is used without epsilon replacement.

Figure Y. Empirical cumulative distribution of the absolute score difference between the floating-point Logistic Regression model and the quantized Logistic Regression relation used by Stage 3.4. The p95 absolute errors are 0.116889 on validation and 0.116913 on test, while rare large deviations remain visible in the log-scaled tail. No zero values were present; a logarithmic x-axis is used without epsilon replacement.

## Recommended Placement

- Exact SHAP margin ECDF: Section 7.4.3.
- Quantization-error ECDF: Section 7.4.1 or Appendix.

## Thesis-Safe Interpretations

Exact SHAP margin ECDF: small rank-3/rank-4 margins identify cases where the inclusion boundary for the public top-3 explanation is empirically fragile. This does not measure proof correctness, does not establish robustness to arbitrary input perturbations, and does not invalidate the certified ranking under the quantized Stage 3.4 relation.

Float-to-quantized LR error ECDF: most score errors are small and binary prediction agreement remains above 99.99% on both splits, but rare larger score deviations exist. The Stage 3.4 proof certifies the quantized integer relation, not exact floating-point equivalence for every possible input.

## Limitations And Concerns

- These analyses reuse saved validation and test arrays and do not retrain any model.
- The Exact SHAP margin figure measures the separation between ranks 3 and 4, not adversarial robustness.
- The LR error figure measures empirical agreement on the saved splits, not formal equivalence over all possible inputs.
- XGBoost is not evaluated in ZK and no hidden-model, model-agnostic SHAP, full provenance, or production-readiness claim is introduced.

## Confirmations

- No Logistic Regression or XGBoost model was retrained.
- No preprocessing, saved models, semantic groups, quantization parameters, Circom circuits, or existing reports were modified.
- The script checks all target files before execution and refuses to overwrite existing files.
- Full arrays are stored in compressed NPZ files; no one-row-per-sample CSV was exported.
