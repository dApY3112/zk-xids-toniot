# Thesis Technical Results Audit

Generated: 2026-06-14

This audit checks which technical result figures/tables can already be added to the thesis from existing ZK-XIDS repository artifacts, and which ones require plotting, model inference, rerunning an analysis pipeline, or additional instrumentation. No models were retrained, no circuits were modified, no plots were generated, and no existing experiment files were changed during this audit.

Status labels:

- `READY`: Existing final figure/table artifact is already available, or the existing artifact can be used directly in the thesis.
- `PLOT_ONLY`: The required source data already exists, and only a lightweight non-overwriting plotting/table-export step is needed.
- `INFERENCE_REQUIRED`: Saved models and split data exist, but model scoring or decision-function computation must be rerun.
- `EXPERIMENT_REQUIRED`: A larger analysis pipeline must be rerun or extended to save the required per-sample data.
- `PARTIAL`: Some evidence exists, but raw data, alignment, validation, or exact requested format is incomplete.
- `MISSING`: Sufficient evidence and reproducible generation path were not found.

Important scope note:

- Stage 3.4 remains the main ZK claim: public Logistic Regression model, private processed input `x_shifted[104]`, public prediction `y_hat`, and public ordered top-3 semantic group IDs.
- Stage 3.5 input commitment remains appendix-only.
- This audit does not support claims about hidden-model support, arbitrary-model SHAP, XGBoost-in-ZK, differential privacy, full provenance, or production deployment.

## A. Precision-Recall Curves

| Technical addition | Status | Existing evidence | Exact repository-relative paths | Relevant variables or columns | Dataset split and sample count | Float or quantized | Matches thesis values? | Can generate without rerun? | Required action |
|---|---|---|---|---|---|---|---|---|---|
| Attack-positive PR curves for XGBoost and Logistic Regression on test split | READY | Existing PNG figures and JSON curve AUCs are present. The script generates PR curves from `y_test` and `p_test` with Attack as positive class. | `reports/figures/decision_engineering_xgboost_pr.png`; `reports/figures/decision_engineering_logistic_regression_pr.png`; `outputs/reports/decision_engineering_baselines.json`; `tools/eval_decision_engineering.py` | JSON keys: `models.*.figures.pr`, `models.*.curves.pr_auc`; script function `_plot_curves(y_test, p_test, ...)` | Test split, `n = 502628` | Floating-point model probabilities | XGBoost PR-AUC in decision-engineering JSON is `0.9999972099`, matching thesis rounded `0.999997`; Logistic Regression PR-AUC is `0.9986725463`, close to thesis baseline `0.998669` but from decision-engineering script. | Yes, existing PNGs can be used directly. Regeneration requires inference and overwrites the existing figures. | Use existing PR figures only if PR curves are really needed. Prefer appendix; main text tables are clearer. |
| Normal-positive PR curves for XGBoost and Logistic Regression | INFERENCE_REQUIRED | Normal PR-AUC scalar values exist in `baseline_metrics_extended.json`, but no Normal-positive PR curve images or precision/recall arrays were found. | `outputs/reports/baseline_metrics_extended.json`; `tools/baseline_metrics.py`; `outputs/processed/y_test.npy`; `outputs/models/*.pkl` | JSON metrics: `pr_auc_normal`; script computes `y_true_normal = (y_true == 0)` and `y_prob_normal = 1 - y_prob_attack` | Test split, `n = 502628`; validation data also exists | Floating-point model probabilities | Scalar Normal PR-AUC values match thesis: XGBoost `0.998401`, Logistic Regression `0.726311`. | No. Model probabilities must be recomputed or saved. | Not recommended for main Chapter 7. If needed, add a lightweight non-overwriting script to load models and plot Normal-positive PR curves. |
| Validation PR curves | INFERENCE_REQUIRED | Validation labels and models exist, but no saved validation PR figures or precision/recall arrays were found. | `outputs/processed/X_val.npy`; `outputs/processed/y_val.npy`; `outputs/models/xgboost_baseline.pkl`; `outputs/models/logreg_baseline.pkl` | Need `predict_proba(X_val)[:, 1]` and `precision_recall_curve` | Validation split, `n = 502628` | Floating-point model probabilities | Not directly checked because no validation PR curve artifact exists. | No. Requires model inference. | Not recommended unless a validation-specific figure is needed for appendix. |
| Saved precision/recall arrays | MISSING | No saved precision arrays, recall arrays, or PR threshold arrays were found. Existing scripts generate plots directly. | `tools/eval_decision_engineering.py`; `reports/figures/decision_engineering_*_pr.png` | Not saved; generated locally inside `_plot_curves` as `prec`, `rec`, `_` | Test split in existing script | Floating-point model probabilities | Existing plots are consistent with reported AUCs, but arrays are absent. | No. | If exact curve data is needed, modify a copy of the plotting script to export arrays to a new CSV/NPZ. |

## B. Logistic Regression Score Distribution

| Technical addition | Status | Existing evidence | Exact repository-relative paths | Relevant variables or columns | Dataset split and sample count | Float or quantized | Matches thesis values? | Can generate without rerun? | Required action |
|---|---|---|---|---|---|---|---|---|---|
| Floating-point Logistic Regression score distribution by true class or predicted class | INFERENCE_REQUIRED | Saved LR model and processed splits exist. No full per-sample LR logits/decision-function arrays were found. | `outputs/models/logreg_baseline.pkl`; `outputs/processed/X_val.npy`; `outputs/processed/y_val.npy`; `outputs/processed/X_test.npy`; `outputs/processed/y_test.npy`; `tools/eval_float_quantized_lr_agreement.py` | Need `float_score = X @ w_float + b_float` or model decision function; no saved full score column | Validation and test, each `n = 502628` | Floating-point LR score/logit | Aggregate agreement/error values match thesis, but full score distribution is not saved. | No. | Requires lightweight LR scoring over saved arrays; no retraining needed. Optional appendix only. |
| Floating-point versus quantized score comparison | INFERENCE_REQUIRED | Script computes scores and summary error, but only aggregate JSON and 20 examples are saved. | `tools/eval_float_quantized_lr_agreement.py`; `outputs/reports/float_vs_quantized_lr_agreement.json`; `outputs/reports/float_vs_quantized_lr_examples.csv`; `stage3_zk/artifacts/model_public.json` | Example CSV columns: `float_score`, `quant_score_scaled`, `score_abs_error`; full arrays not saved | Validation and test, each `n = 502628`; example CSV has 20 rows only | Both floating-point and quantized/scaled integer score | Summary matches thesis: val mean abs error `0.040946`, test mean abs error `0.041297`; prediction agreement over `99.99%`. | No. | Requires rerunning the lightweight scoring computation and saving/plotting full error arrays. |
| Score distribution around selected thresholds | INFERENCE_REQUIRED | Thresholds exist, but per-sample scores/probabilities are not saved. | `outputs/reports/decision_engineering_baselines.json`; `outputs/reports/cost_based_thresholds.json`; `outputs/models/logreg_baseline.pkl`; `outputs/processed/X_test.npy` | Thresholds: LR low-FPR `0.938810`, balanced-MCC `0.088104`, high-recall `0.081597`; default `0.5` | Test split, `n = 502628`; validation split available | Floating-point probabilities or logits, depending plot design | Threshold values match thesis source-of-truth. | No. | Requires inference to compute scores/probabilities. Not necessary for main Chapter 7. |

## C. Exact SHAP Ranking-Margin Distribution

| Technical addition | Status | Existing evidence | Exact repository-relative paths | Relevant variables or columns | Dataset split and sample count | Float or quantized | Matches thesis values? | Can generate without rerun? | Required action |
|---|---|---|---|---|---|---|---|---|---|
| Full Exact SHAP rank-3 versus rank-4 margin histogram/ECDF for validation and test | EXPERIMENT_REQUIRED | The analysis script computes the full margin distribution internally, but only summary statistics and 20 smallest-margin examples are saved. No full per-sample margin array was found. | `tools/analyze_exact_shap_ranking_margin.py`; `outputs/reports/exact_shap_ranking_margin.json`; `outputs/reports/exact_shap_ranking_margin_examples.csv`; `reports/exact_shap_ranking_margin.md` | JSON keys: `margin_scaled_stats`, `small_margin_thresholds_scaled`; example CSV columns: `margin_int`, `margin_scaled`, `top3_ids`, `rank4_id`, `phi_int_by_rank` | Validation and test, each `n = 502628`; example CSV has 20 rows only | Quantized Exact SHAP margin scaled by `Sx * Sw` | Summary values match thesis: median `0.044013`, p5 `0.000411`, `<=0.001` rates `11.1723%` val and `11.0802%` test. | No. | To create a true histogram/ECDF, rerun or extend the margin analysis to save full per-sample margins or plot directly from recomputed margins. Do not approximate from summary stats. |
| Exact SHAP per-sample semantic values for 1100-sample Stage 2 subset | READY | Row-level semantic-group Exact SHAP values exist for the 1100 reconstructed Stage 2 subset. This supports proxy-vs-Exact SHAP figures, not full split margin distribution. | `outputs/explainability/exact_shap_semantic_groups.csv`; `tools/eval_exact_shap_semantic_groups.py`; `reports/figures/thesis/thesis_figure_06_top3_group_frequency_proxy_vs_exact.png`; `reports/figures/thesis/thesis_figure_07_top3_overlap_distribution.png` | CSV columns: `exact_shap_Protocol`, `exact_shap_Application`, `exact_shap_ConnectionState`, `exact_shap_Ports`, `exact_shap_TrafficVolume`, `exact_top3_group_ids`, `top3_overlap_count`, `top3_overlap_jaccard` | Test-derived 1100-sample subset | Floating-point Exact SHAP for public LR | Matches proxy-vs-Exact reported values: mean top-3 overlap `2.0618 / 3`, Jaccard `0.5407`. | Yes, existing figures are ready. | Use existing thesis figures for Section 7.3. Do not treat this subset as the full validation/test margin distribution from Table 7.9. |

## D. Attack-Type Error Breakdown

| Technical addition | Status | Existing evidence | Exact repository-relative paths | Relevant variables or columns | Dataset split and sample count | Float or quantized | Matches thesis values? | Can generate without rerun? | Required action |
|---|---|---|---|---|---|---|---|---|---|
| Full attack-type false-negative table for default, low-FPR, balanced-MCC, high-recall points | PLOT_ONLY | CSV and JSON already contain per-attack-family counts and FN rates for both models and four operating points. A pivot table for thesis can be generated without rerunning inference. | `outputs/reports/attack_type_error_analysis.csv`; `outputs/reports/attack_type_error_analysis.json`; `reports/attack_type_error_analysis.md`; `tools/eval_attack_type_errors.py` | CSV columns: `model`, `point`, `attack_type`, `n`, `tp`, `fn`, `attack_recall`, `fn_rate`, `source_files` | Test split, `n = 502628`; attack types with at least 100 true attack rows | Floating-point model predictions/probabilities at thresholds | Ransomware values match thesis: XGBoost default `0.106790`, XGBoost balanced-MCC `0.103704`, LR default `0.922840`, LR balanced-MCC `0.477160`. | Yes for a pivot/export from existing CSV. | Add a compact table or appendix table. Use attack-type rows only; do not use XGBoost aggregate operating-point rows from this report as final baseline metrics. |
| Verification that `type` is post-hoc metadata only | READY | Script reconstructs metadata from raw sampled files, uses only `label` and `type`, aligns with `test_idx`, and reports zero label mismatches. Preprocessing notebook drops `type` from training. | `tools/eval_attack_type_errors.py`; `notebooks/03_preprocessing_pipeline.ipynb`; `outputs/splits/data_manifest.json`; `outputs/splits/test_idx.npy`; `reports/attack_type_error_analysis.md` | Script: `_load_type_metadata`, `test_meta = metadata.iloc[test_idx]`, `mismatch_count`; notebook: `DROP_COLS = ["src_ip", "dst_ip", "type", "ts"]` | Test split, `n = 502628`; metadata reconstructed from 23 sampled files | Metadata, not model feature | `label_mismatch_count = 0`; `min_count = 100`. | Yes, existing report states the checks. | Use this as wording support: attack type is used only after prediction. |

## E. Quantization-Error Distribution

| Technical addition | Status | Existing evidence | Exact repository-relative paths | Relevant variables or columns | Dataset split and sample count | Float or quantized | Matches thesis values? | Can generate without rerun? | Required action |
|---|---|---|---|---|---|---|---|---|---|
| Full absolute score-error histogram/ECDF | INFERENCE_REQUIRED | Aggregate error summary exists, but full per-sample error array is not saved. The script computes errors internally by chunk. | `tools/eval_float_quantized_lr_agreement.py`; `outputs/reports/float_vs_quantized_lr_agreement.json`; `outputs/reports/float_vs_quantized_lr_examples.csv` | JSON keys: `score_abs_error.mean`, `score_abs_error.p95`, `score_abs_error.max`; example CSV column `score_abs_error` for 20 rows only | Validation and test, each `n = 502628`; example CSV 20 rows | Float LR score vs quantized/scaled LR score | Summary matches thesis: val p95 about `0.116889`, max `161.208082`; test p95 about `0.116913`, max `154.911022`. | No. | Requires rerunning LR scoring/quantized scoring and saving or plotting all per-sample errors. Do not infer histogram from mean/p95/max. |
| Error distribution for prediction-mismatch samples only | PARTIAL | 20 representative examples include two prediction mismatches and other top-3 mismatches, but not all mismatch rows. | `outputs/reports/float_vs_quantized_lr_examples.csv`; `outputs/reports/float_vs_quantized_lr_agreement.json` | Example CSV: `kind`, `float_score`, `quant_score_scaled`, `score_abs_error`, `float_pred`, `quant_pred` | Example subset only; full val/test mismatch sets not saved | Float and quantized | Mismatch counts match thesis: val `44`, test `29`; full rows absent. | No. | If needed, rerun the agreement analysis with a new output that saves all prediction-mismatch rows. |
| Relationship between score error and distance from decision boundary | INFERENCE_REQUIRED | Score and error arrays are not saved. | `tools/eval_float_quantized_lr_agreement.py`; `outputs/models/logreg_baseline.pkl`; `outputs/processed/X_val.npy`; `outputs/processed/X_test.npy` | Need per-sample `float_score`, `quant_score_scaled`, `score_abs_error`, and `abs(float_score)` or `abs(quant_score_scaled)` | Validation/test, `n = 502628` each | Float and quantized | Not directly available. | No. | Optional appendix only; main text already has adequate Table 7.7/7.8 evidence. |

## F. Confusion-Matrix Figures

| Technical addition | Status | Existing evidence | Exact repository-relative paths | Relevant variables or columns | Dataset split and sample count | Float or quantized | Matches thesis values? | Can generate without rerun? | Required action |
|---|---|---|---|---|---|---|---|---|---|
| Side-by-side default-threshold confusion-matrix figure from validated counts | PLOT_ONLY | Exact confusion counts are saved in baseline JSON and match thesis values. Full prediction arrays are not saved, but counts are sufficient for a confusion-matrix figure. | `outputs/reports/baseline_metrics_extended.json`; `reports/baseline_extended_metrics.md`; `tools/baseline_metrics.py` | JSON path: `models.xgboost.default_0.5.confusion`; `models.logistic_regression.default_0.5.confusion`; class order Normal `0`, Attack `1` | Test split, `n = 502628` | Floating-point model probabilities thresholded at `0.5` | Yes. XGBoost `17750/277/179/484422`; LR `16426/1601/31491/453110`. | Yes for plotting from counts. No for reproducing predictions unless inference is rerun. | If a visual confusion matrix is desired, plot directly from JSON counts to a new non-overwriting figure. Main text can also use the counts in prose/table. |
| Saved labels and predictions that reproduce confusion counts | PARTIAL | Saved labels exist, but saved per-sample predictions/probabilities were not found. Saved models and X arrays can reproduce them. | `outputs/processed/y_test.npy`; `outputs/processed/X_test.npy`; `outputs/models/xgboost_baseline.pkl`; `outputs/models/logreg_baseline.pkl` | Need `predict_proba(X_test)[:, 1] >= 0.5`; predictions not saved | Test split, `n = 502628` | Floating-point model probabilities | Counts in JSON match thesis. Per-sample prediction arrays absent. | No. | Rerun inference only if raw prediction arrays are required. |

## G. Circuit Constraint Breakdown

| Technical addition | Status | Existing evidence | Exact repository-relative paths | Relevant variables or columns | Dataset split and sample count | Float or quantized | Matches thesis values? | Can generate without rerun? | Required action |
|---|---|---|---|---|---|---|---|---|---|
| Total Stage 3.4 circuit statistics table | READY | Total constraints, wires, public/private inputs, and artifact sizes are available. | `stage3_zk/reports/STAGE34_PROOF_REPORT.json`; `stage3_zk/reports/STAGE34_PROOF_REPORT.md`; `stage3_zk/circuits/exact_shap_top3/build/exact_shap_top3.r1cs`; `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom` | JSON keys: `circuit_stats.constraints`, `circuit_stats.wires`, `public_inputs`, `private_inputs`, `artifact_sizes` | Circuit artifact, not dataset split | Quantized circuit relation | Matches thesis: constraints `8358`, wires `8078`, public inputs `109`, private inputs `106`. | Yes, existing table is ready. | Use existing Stage 3.4 proof-cost table and thesis figures. |
| Per-component constraint breakdown by input range checks, LR inference, Exact SHAP, absolute values, top-3 checks, ranking/dominance | PARTIAL | Circom source and `.sym`/`.r1cs` build artifacts exist, but no compiler per-template/per-component constraint-count report was found. Existing reports only give total constraints. | `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`; `stage3_zk/circuits/exact_shap_top3/build/exact_shap_top3.sym`; `stage3_zk/circuits/exact_shap_top3/build/exact_shap_top3.r1cs`; `stage3_zk/reports/STAGE34_PROOF_REPORT.json` | Total only: `constraints = 8358`; no per-component columns | Circuit artifact, not dataset split | Quantized circuit relation | Total matches thesis; breakdown not available. | No. | Not recommended for Chapter 7 unless separate compilation/instrumentation is performed. Do not estimate from source line counts or loops. |

## H. Existing Technical Figures and Tables

| Technical addition | Status | Existing evidence | Exact repository-relative paths | Relevant variables or columns | Dataset split and sample count | Float or quantized | Matches thesis values? | Can generate without rerun? | Required action |
|---|---|---|---|---|---|---|---|---|---|
| Thesis-facing Stage 3 and explanation figures | READY | A thesis figure package already exists. It covers framework, semantic grouping, stage progression, constraints, prove/verify time, proxy-vs-Exact SHAP group frequency, overlap distribution, and case-study bars. | `reports/figures/thesis/thesis_figure_01_framework.png`; `reports/figures/thesis/thesis_figure_02_semantic_grouping_pipeline.png`; `reports/figures/thesis/thesis_figure_03_stage_progression.png`; `reports/figures/thesis/thesis_figure_04_constraints_by_stage.png`; `reports/figures/thesis/thesis_figure_05_prove_verify_time_by_stage.png`; `reports/figures/thesis/thesis_figure_06_top3_group_frequency_proxy_vs_exact.png`; `reports/figures/thesis/thesis_figure_07_top3_overlap_distribution.png`; `reports/figures/thesis/thesis_figure_08_case_study_group_bars.png`; `reports/thesis_figures.md`; `tools/generate_thesis_figures.py` | Inputs: `outputs/explainability/exact_shap_semantic_groups.csv`, `stage3_zk/reports/STAGE34_PROOF_REPORT.json`, hardcoded earlier-stage metrics in generator | Exact SHAP subset `n = 1100`; Stage 3.4 samples `1-8`; circuit stats | Mix: floating-point Exact SHAP subset and quantized Stage 3.4 stats | Matches key thesis values for proxy-vs-Exact overlap and Stage 3.4 constraint/proof-cost figures. | Yes, existing PNGs can be used directly. | Use Figure 6 in Section 7.3 and Figures 4/5 in Section 7.5. Figure 8 is optional. |
| Existing ML evaluation figures | READY | ROC, PR, FPR-vs-recall, reliability, cost-threshold, drift, and semantic-ablation PNGs already exist. | `reports/figures/decision_engineering_xgboost_pr.png`; `reports/figures/decision_engineering_logistic_regression_pr.png`; `reports/figures/decision_engineering_*_roc.png`; `reports/figures/decision_engineering_*_fpr_vs_recall.png`; `reports/figures/decision_engineering_*_reliability_*.png`; `reports/figures/cost_thresholds_*.png`; `reports/figures/drift_chunks_*.png`; `reports/figures/semantic_group_ablation_*.png` | See `outputs/reports/decision_engineering_baselines.json`, `outputs/reports/cost_based_thresholds.json`, `outputs/reports/drift_chunks.json`, `outputs/reports/semantic_group_ablation.json` | Mostly test split or summarized robustness experiments | Floating-point ML results | Existing figures align with their generating reports; use final source-of-truth values for thesis tables. | Yes, existing PNGs can be used directly. | Keep most of these in appendix. Main text should prefer compact tables. |
| Missing high-priority distribution figures | EXPERIMENT_REQUIRED | No existing margin histogram/ECDF or quantization-error histogram/ECDF was found. | Candidate inputs: `outputs/processed/X_val.npy`, `outputs/processed/X_test.npy`, `stage3_zk/artifacts/model_public.json`, `stage3_zk/artifacts/exact_shap_reference.json`, `tools/analyze_exact_shap_ranking_margin.py`, `tools/eval_float_quantized_lr_agreement.py` | Full per-sample arrays not saved | Validation/test, each `n = 502628` | Quantized Exact SHAP margins; float-vs-quantized LR errors | Summary statistics match thesis, but distributions absent. | No. | Only add if willing to rerun/extend analysis and save new non-overwriting figure artifacts. |

## Commands for READY or PLOT_ONLY Items

These commands are proposed only. They were not executed during this audit.

### Use Existing Figures Directly

No command is needed to include existing figures in the thesis:

- `reports/figures/thesis/thesis_figure_06_top3_group_frequency_proxy_vs_exact.png`
- `reports/figures/thesis/thesis_figure_04_constraints_by_stage.png`
- `reports/figures/thesis/thesis_figure_05_prove_verify_time_by_stage.png`
- `reports/figures/thesis/thesis_figure_08_case_study_group_bars.png` (optional)
- `reports/figures/decision_engineering_xgboost_pr.png` (appendix if needed)
- `reports/figures/decision_engineering_logistic_regression_pr.png` (appendix if needed)

Existing generator commands are available, but they write to existing output paths and should not be run unless intentionally regenerating:

```powershell
python tools/generate_thesis_figures.py
python tools/eval_decision_engineering.py
```

### Proposed Non-Overwriting Attack-Type Pivot Table

Input:

- `outputs/reports/attack_type_error_analysis.csv`

Expected output:

- `reports/attack_type_error_pivot_for_thesis.md`

Proposed command:

```powershell
python -c "import pandas as pd; p='outputs/reports/attack_type_error_analysis.csv'; df=pd.read_csv(p); keep=['default_0.5','balanced_mcc']; df=df[df['point'].isin(keep)]; piv=df.pivot_table(index=['attack_type','n'], columns=['model','point'], values='fn_rate', aggfunc='first').reset_index(); piv.to_markdown('reports/attack_type_error_pivot_for_thesis.md', index=False)"
```

### Proposed Non-Overwriting Confusion-Matrix Figure

Input:

- `outputs/reports/baseline_metrics_extended.json`

Expected output:

- `reports/figures/thesis_extra/confusion_matrices_default_counts.png`

Proposed command:

```powershell
python -c "import json, pathlib, numpy as np, matplotlib.pyplot as plt; data=json.load(open('outputs/reports/baseline_metrics_extended.json', encoding='utf-8')); out=pathlib.Path('reports/figures/thesis_extra'); out.mkdir(parents=True, exist_ok=True); fig,axs=plt.subplots(1,2,figsize=(7,3.2)); names=[('xgboost','XGBoost'),('logistic_regression','Logistic Regression')]; [ax.set_axis_off() for ax in axs];\nfor ax,(key,title) in zip(axs,names):\n c=data['models'][key]['default_0.5']['confusion']; mat=np.array([[c['tn'],c['fp']],[c['fn'],c['tp']]]); ax.imshow(mat,cmap='Blues'); ax.set_title(title); ax.set_xticks([0,1],['Pred Normal','Pred Attack']); ax.set_yticks([0,1],['True Normal','True Attack']);\n [ax.text(j,i,f'{mat[i,j]:,}',ha='center',va='center') for i in range(2) for j in range(2)];\nfig.tight_layout(); fig.savefig(out/'confusion_matrices_default_counts.png', dpi=180)"
```

Note: the one-line PowerShell command above contains embedded newlines for readability. If using it, paste it into a script or convert it to a single-line Python command.

## Final Priority Summary

### 1. Can be added immediately from existing figures or tables

Highest-value ready additions:

1. `reports/figures/thesis/thesis_figure_06_top3_group_frequency_proxy_vs_exact.png`
   - Recommended for Section 7.3.3.
2. `reports/figures/thesis/thesis_figure_04_constraints_by_stage.png`
   - Recommended for Section 7.5.2.
3. `reports/figures/thesis/thesis_figure_05_prove_verify_time_by_stage.png`
   - Recommended for Section 7.5.2.
4. `outputs/reports/attack_type_error_analysis.csv`
   - Ready for an appendix or compact pivot table.
5. `reports/figures/thesis/thesis_figure_08_case_study_group_bars.png`
   - Optional; Table 7.12 may already be enough.

### 2. Requires plotting only

1. Attack-type pivot table from `outputs/reports/attack_type_error_analysis.csv`.
2. Confusion-matrix figure from validated counts in `outputs/reports/baseline_metrics_extended.json`.

These can be generated without model inference, but they are not essential if Chapter 7 already has clear tables.

### 3. Requires lightweight model inference but no retraining

1. Normal-positive PR curves.
2. Validation PR curves.
3. Logistic Regression score distributions.
4. Full quantization-error histograms/ECDFs.
5. Score-error versus decision-boundary plots.

These are optional and probably appendix-only.

### 4. Requires rerunning an analysis experiment

1. Exact SHAP ranking-margin histogram/ECDF for full validation/test splits.

This is the most relevant missing technical figure, but the current artifacts only save summary statistics and 20 examples. A true histogram/ECDF requires recomputing or saving full per-sample margins. Do not approximate from Table 7.9.

### 5. Missing or not recommended

1. Per-component Stage 3.4 constraint breakdown.
   - Only total constraints are available. Per-component counts require instrumentation or separate compilation.
2. Additional PR/ROC/calibration figures in main text.
   - Existing tables communicate the result more cleanly.
3. Extra 7.6/7.7 figures.
   - Use compact tables/prose for leakage, reference sensitivity, Stage 3.5, and RQ summary.

## Recommended Thesis Decision

For the current Chapter 7 draft, the best figure set is:

- Section 7.3.3: `reports/figures/thesis/thesis_figure_06_top3_group_frequency_proxy_vs_exact.png`
- Section 7.5.2: `reports/figures/thesis/thesis_figure_04_constraints_by_stage.png`
- Section 7.5.2: `reports/figures/thesis/thesis_figure_05_prove_verify_time_by_stage.png`

Do not add new figures to Sections 7.6 and 7.7. Use one compact table for leakage/reference/Stage 3.5 if needed, and a prose summary or small RQ mapping table for the final section.

