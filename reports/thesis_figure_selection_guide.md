# Thesis Figure Selection Guide

Generated: 2026-05-24

## Recommendation

Use the new thesis figure package under `reports/figures/thesis/` as the main visual backbone. The older Stage 2 and ML evaluation figures are useful supporting artifacts, but most should be moved to appendix or converted into tables so the thesis does not read like a generic IDS benchmarking report.

The main thesis story should be:

```text
proof pattern -> semantic abstraction -> circuit progression -> proof overhead -> Exact SHAP explanation behavior
```

## Main Text Figures

Use these in the main Method/Results chapters.

| Priority | File | Use | Reason |
|---:|---|---|---|
| 1 | `reports/figures/thesis/thesis_figure_01_framework.png` | Main framework figure | Shows public-model/private-input verification, model registry, proof, and intentional outputs. |
| 2 | `reports/figures/thesis/thesis_figure_02_semantic_grouping_pipeline.png` | Method figure | Explains the semantic-group abstraction from 104 features to 5 explanation players. |
| 3 | `reports/figures/thesis/thesis_figure_03_stage_progression.png` | Method/system figure | Shows how Stage 3.1-3.4 develop from inference to verified Exact SHAP. |
| 4 | `reports/figures/thesis/thesis_figure_04_constraints_by_stage.png` | Results figure | Shows proof cost across stages. |
| 5 | `reports/figures/thesis/thesis_figure_05_prove_verify_time_by_stage.png` | Results figure | Shows practical proving and verification overhead. |
| 6 | `reports/figures/thesis/thesis_figure_06_top3_group_frequency_proxy_vs_exact.png` | Results/XAI figure | Shows old proxy vs Exact SHAP explanation behavior. |
| 7 | `reports/figures/thesis/thesis_figure_07_top3_overlap_distribution.png` | Results/XAI figure | Shows how often the old proxy and Exact SHAP agree or differ. |
| 8 optional | `reports/figures/thesis/thesis_figure_08_case_study_group_bars.png` | Discussion/case-study figure | Good if there is space; otherwise keep the case-study table only. |

## Existing Stage 2 Figures

| File | Recommendation | Why |
|---|---|---|
| `outputs/stage2/fig_top10_logreg.png` | Appendix or convert to table | Useful historical Stage 2 artifact, but too feature-level for the final thesis framing. |
| `outputs/stage2/fig_top10_xgb.png` | Appendix or convert to table | Shows XGBoost feature behavior, but XGBoost is not the ZK model. Keep as supporting baseline only. |
| `outputs/stage2/fig_semantic_groups_logreg.png` | Optional appendix; usually superseded by thesis Figure 6 | Stage 2 semantic frequency is useful background, but the old-proxy-vs-ExactSHAP figure is more thesis-relevant. |
| `outputs/stage2/fig_semantic_groups_xgb.png` | Appendix only | Useful for baseline comparison, not central to Stage 3.4 proof contribution. |

Recommendation: do not put the Stage 2 top-10 feature figures in the main Results chapter. If needed, include a compact table of the top features/groups in an appendix.

## Existing ML Evaluation Figures

| File pattern | Recommendation | Why |
|---|---|---|
| `reports/figures/decision_engineering_*_roc.png` | Appendix or omit | ROC curves are highly saturated and less informative for the thesis core. Use metric tables instead. |
| `reports/figures/decision_engineering_*_pr.png` | Appendix, not main text | PR curves show strong baseline performance, but the main claim is not model benchmarking. |
| `reports/figures/decision_engineering_*_fpr_vs_recall.png` | Optional main/appendix | Most useful ML curve because IDS false alarms matter. Include at most one combined discussion or keep table. |
| `reports/figures/decision_engineering_*_reliability_raw.png` | Appendix or omit | Calibration supports decision engineering but is not central to verifiable explanations. |
| `reports/figures/decision_engineering_*_reliability_platt.png` | Appendix or omit | Same as above. |
| `reports/figures/decision_engineering_*_reliability_isotonic.png` | Appendix or omit | Same as above. |
| `reports/figures/drift_chunks_logistic_regression.png` | Appendix or short robustness section | Useful self-assessment for LR but visually dense. Better summarized in text/table unless robustness is a major chapter. |
| `reports/figures/drift_chunks_xgboost.png` | Appendix | Supports XGBoost baseline robustness, not central to ZK proof contribution. |
| `reports/figures/semantic_group_ablation_logistic_regression.png` | Optional appendix or one supporting figure | Useful for explaining group-size bias in old attribution. Main text can cite the table in `reports/semantic_group_ablation.md`. |
| `reports/figures/semantic_group_ablation_xgboost.png` | Appendix | Useful only for baseline comparison. |
| `reports/figures/cost_thresholds_logistic_regression.png` | Convert to table or appendix | The plot is large and decision-engineering focused. The cost table communicates the result more cleanly. |
| `reports/figures/cost_thresholds_xgboost.png` | Convert to table or appendix | Same as above. |

## Convert to Tables

Use tables instead of figures for these results:

| Result | Source | Why table is better |
|---|---|---|
| Baseline model metrics | `reports/baseline_extended_metrics.md` | The key numbers are balanced accuracy, MCC, recall, specificity, FPR, and PR-AUC. |
| Operating points | `reports/decision_engineering_baselines.md` | Threshold, FPR, recall, MCC, and confusion matrix are clearer as rows. |
| Calibration values | `reports/decision_engineering_baselines.md` | Brier/ECE values are compact and do not need reliability plots in main text. |
| Cost-based thresholds | `reports/cost_based_thresholds.md` | The threshold/FPR/recall/cost trade-off is clearer as a table. |
| Stage 2 top-10 feature frequencies | `outputs/stage2/top10_frequency_*.csv` | Feature-level bars are visually heavy and less central than semantic groups. |
| Exact SHAP correctness validation | `reports/stage34_thesis_integration.md` | Numerical residuals are near zero, so a figure would be visually uninformative. |
| Negative tests | `reports/stage34_thesis_integration.md` | Pass/fail security cases are best as a compact table. |

## Suggested Final Figure Count

For a clean thesis, use:

- 7 main figures: thesis Figure 1-7.
- Optional 8th figure: case-study bars.
- 0-2 appendix figures from the old ML/Stage 2 set.

Avoid putting more than 10 figures in the main body. The strongest thesis narrative comes from fewer figures that directly support the verifiable semantic explanation framework.

## Suggested Appendix Figures

If the thesis has an appendix, include:

- `outputs/stage2/fig_top10_logreg.png`
- `outputs/stage2/fig_top10_xgb.png`
- `reports/figures/semantic_group_ablation_logistic_regression.png`
- optionally one PR or FPR-vs-recall figure for each model

Everything else can remain as reproducibility artifacts in the repository without being shown in the thesis.
