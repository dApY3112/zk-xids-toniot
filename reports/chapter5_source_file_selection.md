# Chapter 5 Source File Selection

Generated: 2026-05-26

Chapter 5 title:

> Semantic Explainability and Group-Level Attribution

This file lists the repository sources that are necessary or strongly useful for writing Chapter 5. The focus is Stage 2 explainability, semantic grouping, attribution stability, group-size ablation, and the transition from the older grouped attribution proxy to semantic-group Exact SHAP.

Chapter 5 should not become a full ZK proof chapter. Stage 3.4 can be mentioned as the motivation for upgrading the explanation target, while circuit design and proof benchmarks should remain in Chapter 6.

## A. Essential Files for Chapter 5

| File | Why it is needed | Supports | Priority |
|---|---|---|---|
| `reports/stage2_summary.md` | Main Stage 2 narrative. Defines raw top-k attribution, k=5, 1100-sample subset, LogReg `abs(w_i*x_i)`, XGBoost `pred_contribs=True`, raw stability, semantic stability, and relevance to Stage 3. | 5.1, 5.2, 5.3, 5.4, 5.6 | Essential |
| `outputs/stage2/stability_summary.json` | Exact raw feature-level stability values: LogReg `0.5846640410550185`, XGBoost `0.4075426661892827`, k=5, subset size 1100. | 5.2 | Essential |
| `outputs/stage2/overlap_summary.json` | Exact raw LogReg-XGBoost overlap: mean Jaccard `0.15575036075036072`, std `0.0819668899212029`. | 5.2 | Essential |
| `outputs/stage2/semantic_stability_summary.json` | Exact semantic stability values: LogReg `0.779423558897243`, XGBoost `0.7428989139515455`. | 5.4 | Essential |
| `outputs/stage2/semantic_overlap_summary.json` | Exact semantic LogReg-XGBoost overlap: mean Jaccard `0.3011969696969697`, std `0.14676763601256326`. | 5.4 | Essential |
| `outputs/stage2/top10_frequency_logreg.csv` | Raw LogReg feature-frequency table for top-k explanations. Supports writing the raw feature attribution subsection and optional table. | 5.1 | Essential |
| `outputs/stage2/top10_frequency_xgb.csv` | Raw XGBoost feature-frequency table for top-k explanations. Supports model comparison at raw feature level. | 5.1 | Essential |
| `outputs/stage2/semantic_group_frequency_logreg.csv` | LogReg semantic group frequency: Application `100.00%`, Protocol `99.91%`, ConnectionState `45.55%`, Ports `6.36%`, TrafficVolume `6.18%`. | 5.3, 5.4, 5.5 | Essential |
| `outputs/stage2/semantic_group_frequency_xgb.csv` | XGBoost semantic group frequency: TrafficVolume `99.55%`, Ports `95.91%`, Protocol `74.82%`, ConnectionState `66.64%`, Application `7.00%`. | 5.3, 5.4, 5.5 | Essential |
| `reports/semantic_group_ablation.md` | Gives group sizes, raw frequency, size-normalized frequency, and top-3 rankings. Verifies group-size bias and normalized rankings. | 5.5 | Essential |
| `stage3_zk/artifacts/group_map.json` | Machine-readable definition of the five semantic groups, group IDs, and feature-index-to-group mapping. | 5.3 | Essential |
| `stage3_zk/artifacts/feature_order.json` | Feature names/order needed to interpret `group_map.json` and raw top-k feature indices. | 5.1, 5.3 | Essential |
| `reports/exact_shap_semantic_groups.md` | Main Exact SHAP result report. Explains semantic-group Exact SHAP definition, value function, reference vector, old proxy comparison, and known values: overlap `2.0618 / 3`, Jaccard `0.5407`. | 5.6 | Essential |
| `reports/method_choice_exact_shap.md` | Explains why the old grouped attribution proxy is useful but not a Shapley explanation, why Exact SHAP is academically stronger, and why five semantic groups make exact enumeration feasible. | 5.6 | Essential |
| `outputs/explainability/exact_shap_semantic_groups.csv` | Row-level Exact SHAP vs old proxy comparison, including old/exact top-3 groups, overlap, Jaccard, and group values. Useful for tables or figures. | 5.6 | Essential |

## B. Useful Optional Files

| File | Why it may help | Supports | Priority |
|---|---|---|---|
| `notebooks/05_stage2_topk_explainability.ipynb` | Implementation source for raw top-k explanation generation. Useful if the writing assistant needs code-level details. | 5.1, 5.2 | Optional |
| `notebooks/05b_stage2_semantic_grouping.ipynb` | Implementation source for semantic grouping and semantic stability/overlap. | 5.3, 5.4 | Optional |
| `tools/eval_semantic_group_ablation.py` | Reproducibility script for group-size ablation. Useful for method appendix or implementation detail. | 5.5 | Optional |
| `tools/eval_exact_shap_semantic_groups.py` | Exact SHAP computation script. Useful for algorithmic details in 5.6. | 5.6 | Optional |
| `reports/stage34_thesis_integration.md` | Useful only for the transition sentence from old proxy to Stage 3.4 Exact SHAP. Do not use the proof benchmark table in Chapter 5. | 5.6 | Optional |
| `reports/thesis_figures.md` | Lists generated thesis figures, including proxy-vs-ExactSHAP figures. | 5.3, 5.5, 5.6 | Optional |
| `reports/thesis_figure_selection_guide.md` | Explains which figures to use in the thesis and which old figures should be appendix/table only. | 5.1-5.6 | Optional |
| `reports/figures/thesis/thesis_figure_02_semantic_grouping_pipeline.png` | Useful figure for semantic grouping construction. | 5.3 | Optional |
| `reports/figures/thesis/thesis_figure_06_top3_group_frequency_proxy_vs_exact.png` | Main figure for old proxy vs Exact SHAP group-frequency behavior. | 5.6 | Optional |
| `reports/figures/thesis/thesis_figure_07_top3_overlap_distribution.png` | Main figure for old proxy vs Exact SHAP top-3 overlap distribution. | 5.6 | Optional |
| `outputs/stage2/fig_top10_logreg.png` | Appendix-only raw top-10 feature figure. Prefer table in main text. | 5.1 | Optional |
| `outputs/stage2/fig_top10_xgb.png` | Appendix-only raw top-10 feature figure. Prefer table in main text. | 5.1 | Optional |
| `outputs/stage2/fig_semantic_groups_logreg.png` | Appendix or supporting figure. Usually superseded by thesis Figure 6 and semantic group tables. | 5.3, 5.4 | Optional |
| `outputs/stage2/fig_semantic_groups_xgb.png` | Appendix or supporting figure. Usually superseded by thesis Figure 6 and semantic group tables. | 5.3, 5.4 | Optional |
| `reports/figures/semantic_group_ablation_logistic_regression.png` | Optional figure for group-size bias. Main text can use the table from `semantic_group_ablation.md`. | 5.5 | Optional |
| `reports/figures/semantic_group_ablation_xgboost.png` | Optional figure for XGBoost group-size bias. Main text can use the table from `semantic_group_ablation.md`. | 5.5 | Optional |

## C. Files Not Needed for Chapter 5

These are useful elsewhere in the thesis but should not be sent as primary Chapter 5 sources.

| File or group | Why not needed for Chapter 5 |
|---|---|
| `stage3_zk/reports/STAGE34_PROOF_REPORT.md` | Chapter 6 proof evidence. Chapter 5 only needs the explanation-method transition, not proof metrics. |
| `stage3_zk/reports/zk_stage34_scaling_benchmark.md` | Proof scaling benchmark belongs in Chapter 6. |
| `stage3_zk/reports/zk_scaling_benchmark.md` | Proof benchmark, not Chapter 5 explainability design. |
| `stage3_zk/reports/LATEST_REPRO_REPORT.md` | General ZK reproducibility report, mostly Chapter 6. |
| `stage3_zk/circuits/**` | Circuit source belongs in Chapter 6, not Chapter 5. |
| `stage3_zk/scripts/**` | Proof scripts belong in Chapter 6 or reproducibility appendix. |
| `reports/model_visibility_threat_model.md` | Threat model belongs in Chapter 4/6, not Chapter 5. |
| `reports/model_registry_and_verifier_policy.md` | Verifier policy belongs in Chapter 6. |
| `reports/formal_framework_and_security_guarantees.md` | Formal proof relation belongs mainly in Chapter 6. Use only if a short scope sentence is needed. |
| `reports/stage34_output_leakage_audit.md` | Output leakage belongs in privacy/security discussion, not core Chapter 5. |
| `reports/exact_shap_reference_sensitivity.md` | Useful for discussion/limitations, but not necessary for the planned Chapter 5 structure. |
| `reports/baseline_extended_metrics.md` | Model performance belongs in Chapter 4 or background results, not explainability design. |
| `reports/decision_engineering_baselines.md` | Threshold/operating-point analysis belongs outside Chapter 5. |
| `reports/cost_based_thresholds.md` | Decision threshold analysis belongs outside Chapter 5. |
| `reports/drift_chunks.md` | Robustness/drift analysis belongs outside Chapter 5. |
| `outputs/processed/**` | Large data arrays, not needed by a writing assistant. |
| `outputs/models/**` | Model binaries, not needed for writing Chapter 5. |
| `outputs/splits/**` | Split arrays, not needed for Chapter 5 writing. |
| `data/**` | Raw/processed data is too large and unnecessary for writing Chapter 5. |

## D. Missing Files to Look For

No critical Chapter 5 source is missing. The repository contains the necessary reports and artifacts.

One optional convenience file would be a human-readable feature-to-semantic-group table generated from `stage3_zk/artifacts/feature_order.json` and `stage3_zk/artifacts/group_map.json`. It is not required because `reports/semantic_group_ablation.md` already gives group sizes and `group_map.json` gives the machine-readable mapping.

## Values Verified from Files

| Claim | Verified value | Source |
|---|---:|---|
| LogReg raw top-5 stability | `0.5846640410550185` | `outputs/stage2/stability_summary.json` |
| XGBoost raw top-5 stability | `0.4075426661892827` | `outputs/stage2/stability_summary.json` |
| Raw LogReg-XGBoost overlap | `0.15575036075036072` | `outputs/stage2/overlap_summary.json` |
| LogReg semantic stability | `0.779423558897243` | `outputs/stage2/semantic_stability_summary.json` |
| XGBoost semantic stability | `0.7428989139515455` | `outputs/stage2/semantic_stability_summary.json` |
| Semantic overlap | `0.3011969696969697` | `outputs/stage2/semantic_overlap_summary.json` |
| Old proxy vs Exact SHAP mean top-3 overlap | `2.0618 / 3` | `reports/exact_shap_semantic_groups.md` |
| Old proxy vs Exact SHAP mean Jaccard | `0.5407` | `reports/exact_shap_semantic_groups.md` |

## Final Minimal Upload Set

Use this smallest upload set for another ChatGPT conversation to write Chapter 5 accurately:

1. `reports/stage2_summary.md`
2. `outputs/stage2/stability_summary.json`
3. `outputs/stage2/overlap_summary.json`
4. `outputs/stage2/semantic_stability_summary.json`
5. `outputs/stage2/semantic_overlap_summary.json`
6. `outputs/stage2/top10_frequency_logreg.csv`
7. `outputs/stage2/top10_frequency_xgb.csv`
8. `outputs/stage2/semantic_group_frequency_logreg.csv`
9. `outputs/stage2/semantic_group_frequency_xgb.csv`
10. `reports/semantic_group_ablation.md`
11. `stage3_zk/artifacts/group_map.json`
12. `stage3_zk/artifacts/feature_order.json`
13. `reports/exact_shap_semantic_groups.md`
14. `reports/method_choice_exact_shap.md`
15. `outputs/explainability/exact_shap_semantic_groups.csv`

If the writing assistant also needs figures, add:

16. `reports/thesis_figures.md`
17. `reports/figures/thesis/thesis_figure_02_semantic_grouping_pipeline.png`
18. `reports/figures/thesis/thesis_figure_06_top3_group_frequency_proxy_vs_exact.png`
19. `reports/figures/thesis/thesis_figure_07_top3_overlap_distribution.png`
