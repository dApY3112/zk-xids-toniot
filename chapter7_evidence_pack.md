# Chapter 7 Evidence Pack - Evaluation and Results

Generated for drafting Chapter 7 of the Master's thesis:

`Zero-Knowledge Framework for Verifiable Semantic Explanations under Private Input: An Intrusion Detection Case Study`

This file is a compact source-of-truth pack for writing Chapter 7. It summarizes the results that should be used in the thesis, points to the source files for each claim, and separates main-text evidence from appendix-only evidence.

## 1. Scope Guardrails

Use this framing throughout Chapter 7:

- Main system claim: public-model/private-input verification for a public Logistic Regression IDS model.
- Main implemented contribution: Stage 3.4 verifies that public `y_hat` and ordered top-3 semantic-group Exact SHAP IDs are computed correctly from the same private processed input witness `x_shifted[104]`.
- Private values: processed input vector and internal Exact SHAP values.
- Public values: approved model artifacts, public weights/bias, public prediction `y_hat`, public ordered top-3 semantic group IDs.
- Stage 3.5 is appendix-only feasibility evidence for an input-commitment binding point.

Do not claim:

- hidden-model support;
- model confidentiality;
- model-agnostic SHAP verification;
- arbitrary-model Exact SHAP;
- Partition SHAP;
- sumcheck/GKR implementation;
- XGBoost-in-ZK;
- differential privacy;
- full SIEM provenance;
- production-ready deployment.

## 2. Authoritative Sources

Use these files first when checking final numbers:

| Topic | Source file |
|---|---|
| Final result checklist | `reports/final_numbers_source_of_truth.md` |
| Project/chapter map | `reports/thesis_project_map.md` |
| Baseline IDS metrics | `reports/baseline_extended_metrics.md` |
| Operating points and calibration | `reports/decision_engineering_baselines.md` |
| Cost-sensitive thresholds | `reports/cost_based_thresholds.md` |
| File-wise holdout robustness | `reports/filewise_holdout.md` |
| Attack-type error analysis | `reports/attack_type_error_analysis.md` |
| Stage 2 raw/semantic explanation stability | `reports/stage2_summary.md` |
| Semantic group-size ablation | `reports/semantic_group_ablation.md` |
| Semantic-group Exact SHAP and proxy comparison | `reports/exact_shap_semantic_groups.md` |
| Float LR vs quantized LR agreement | `reports/float_vs_quantized_lr_agreement.md` |
| Exact SHAP ranking margin | `reports/exact_shap_ranking_margin.md` |
| Stage 3.4 thesis integration | `reports/stage34_thesis_integration.md` |
| Stage 3.4 case studies | `reports/stage34_case_studies.md` |
| Stage 3.4 diverse test vectors | `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md` |
| Stage 3.4 proof report | `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |
| Stage 3.4 supplemental batch smoke test | `stage3_zk/reports/STAGE34_BATCH_SMOKE_REPORT.md` |
| Output leakage audit | `reports/stage34_output_leakage_audit.md` |
| Reference sensitivity | `reports/exact_shap_reference_sensitivity.md` |
| Verifier policy | `reports/model_registry_and_verifier_policy.md` |
| Stage 3.5 appendix | `reports/input_commitment_appendix.md` and `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md` |
| Thesis figure package | `reports/thesis_figures.md` and `reports/thesis_figure_selection_guide.md` |

Consistency warning:

- `reports/attack_type_error_analysis.md` contains XGBoost aggregate operating-point rows that do not match the final baseline/decision-engineering source-of-truth tables. For Chapter 7, use `reports/final_numbers_source_of_truth.md`, `reports/baseline_extended_metrics.md`, and `reports/decision_engineering_baselines.md` for aggregate baseline metrics. Use `reports/attack_type_error_analysis.md` only for post-hoc attack-family false-negative patterns.

## 3. Recommended Chapter 7 Structure

Use a compact thesis-style structure with 7 main sections. The evidence blocks later in this file are not meant to become separate chapter sections; they are source blocks to be folded into the subsections below.

```text
7 EVALUATION AND RESULTS

7.1 Evaluation Setup

7.2 IDS Performance and Decision Behaviour
    7.2.1 Baseline Detection Performance
    7.2.2 Threshold Selection and Calibration
    7.2.3 Robustness and Attack-Type Error Analysis

7.3 Explanation Behaviour
    7.3.1 Raw and Semantic Explanation Stability
    7.3.2 Group-Size Bias
    7.3.3 Proxy Attribution versus Semantic-Group Exact SHAP

7.4 ML-to-ZK Validity
    7.4.1 Float-to-Quantized Logistic Regression Agreement
    7.4.2 Exact SHAP Top-3 Agreement
    7.4.3 Ranking-Margin Analysis

7.5 Zero-Knowledge Proof Evaluation
    7.5.1 Stage 3.4 Correctness and Negative Tests
    7.5.2 Circuit Complexity and Proof Cost
    7.5.3 Diverse Test Vectors and Case Studies

7.6 Privacy, Leakage, and Scope Boundaries
    7.6.1 Public Output Leakage
    7.6.2 Reference Sensitivity
    7.6.3 Optional Input-Commitment Prototype

7.7 Summary of Findings
```

Keep Chapter 7 focused on evidence and interpretation. Do not re-explain all methodology from Chapters 4-6. Stage 3.5 should be a short scope-boundary subsection or appendix pointer, not a main contribution section.

### Evidence-to-Section Map

| Thesis section | Evidence blocks in this file |
|---|---|
| 7.1 Evaluation Setup | Section 4 |
| 7.2 IDS Performance and Decision Behaviour | Sections 5 and 6 |
| 7.3 Explanation Behaviour | Sections 7 and 8 |
| 7.4 ML-to-ZK Validity | Section 9 |
| 7.5 Zero-Knowledge Proof Evaluation | Sections 10, 11, and 12 |
| 7.6 Privacy, Leakage, and Scope Boundaries | Sections 13, 14, and 15 |
| 7.7 Summary of Findings | Section 18 |

## 4. Evaluation Setup Evidence

Use in Section 7.1.

| Item | Value | Source |
|---|---|---|
| Dataset mode | `processed_stratified_sample_23files_frac0.15` | `reports/thesis_project_map.md`, `reports/baseline_extended_metrics.md` |
| Sampling | 15 percent from each of 23 processed files | `reports/stage2_summary.md` |
| Split strategy | stratified 70/15/15 | `reports/stage2_summary.md` |
| Random seed | 42 | `reports/thesis_project_map.md` |
| Feature count | 104 | `reports/thesis_project_map.md` |
| Semantic groups | Protocol, Application, ConnectionState, Ports, TrafficVolume | `reports/thesis_project_map.md`, `reports/exact_shap_semantic_groups.md` |
| Proof-layer model | public Logistic Regression | `reports/stage34_thesis_integration.md` |
| Plaintext baseline | XGBoost | `reports/baseline_extended_metrics.md` |
| Main ZK evidence | Stage 3.4 samples 1-8 | `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |
| Diverse vectors | FP, high-confidence, borderline, near-tie cases | `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md` |
| Supplemental ZK smoke test | 30 deterministic label-balanced Stage 3.4 witnesses, proofs, and verifications | `stage3_zk/reports/STAGE34_BATCH_SMOKE_REPORT.md` |
| Appendix extension | Stage 3.5 input commitment, samples 1, 7, 8 | `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md` |

Interpretation to write:

- XGBoost evaluates the strongest plaintext IDS baseline.
- Logistic Regression is selected for the proof-compatible implementation because the linear score gives a compact circuit relation and a closed-form semantic-group Exact SHAP formula.
- The evaluation therefore has two roles: IDS performance assessment and proof-system validation.

## 5. Baseline IDS Performance

Use in Section 7.2.1.

Source: `reports/final_numbers_source_of_truth.md` and `reports/baseline_extended_metrics.md`.

| Model | Operating point | Threshold | Balanced Acc | MCC | Attack Recall | Normal Recall/Spec | FPR | PR-AUC Attack | PR-AUC Normal | Confusion tn/fp/fn/tp |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| xgboost | default_0.5 | 0.500000 | 0.992132 | 0.986851 | 0.999631 | 0.984634 | 0.015366 | 0.999997 | 0.998401 | 17750/277/179/484422 |
| xgboost | tuned_mcc | 0.489287 | 0.992081 | 0.986907 | 0.999639 | 0.984523 | 0.015477 | 0.999997 | 0.998401 | 17748/279/175/484426 |
| xgboost | tuned_bacc | 0.968393 | 0.996811 | 0.955497 | 0.996729 | 0.996894 | 0.003106 | 0.999997 | 0.998401 | 17971/56/1585/483016 |
| logistic_regression | default_0.5 | 0.500000 | 0.923103 | 0.535818 | 0.935017 | 0.911189 | 0.088811 | 0.998669 | 0.726311 | 16426/1601/31491/453110 |
| logistic_regression | tuned_mcc | 0.088104 | 0.853183 | 0.761031 | 0.994600 | 0.711766 | 0.288234 | 0.998669 | 0.726311 | 12831/5196/2617/481984 |
| logistic_regression | tuned_bacc | 0.620204 | 0.929770 | 0.538253 | 0.933095 | 0.926444 | 0.073556 | 0.998669 | 0.726311 | 16701/1326/32422/452179 |

Main interpretation:

- XGBoost is the stronger plaintext IDS model.
- Logistic Regression is not presented as the best detector; it is the proof-compatible public model.
- Normal recall/specificity and FPR matter because Normal is the minority class and false alarms affect IDS usability.
- LR has high Attack PR-AUC but much weaker Normal PR-AUC and MCC than XGBoost.

Recommended table:

- Table 7.1: Test-set baseline IDS metrics for XGBoost and Logistic Regression.

## 6. Decision Engineering, Calibration, and Robustness

Use in Sections 7.2.2 and 7.2.3.

### 6.1 Operating Points

Source: `reports/final_numbers_source_of_truth.md` and `reports/decision_engineering_baselines.md`.

| Model | Point | Threshold | Attack Recall | Normal Recall/Spec | FPR | MCC | Confusion tn/fp/fn/tp |
|---|---|---:|---:|---:|---:|---:|---|
| xgboost | low_fpr | 0.807750 | 0.999226 | 0.991124 | 0.008876 | 0.984716 | 17867/160/375/484226 |
| xgboost | balanced_mcc | 0.489287 | 0.999639 | 0.984523 | 0.015477 | 0.986907 | 17748/279/175/484426 |
| xgboost | high_recall | 0.984017 | 0.994868 | 0.997615 | 0.002385 | 0.933712 | 17984/43/2487/482114 |
| logistic_regression | low_fpr | 0.938810 | 0.504396 | 0.990015 | 0.009985 | 0.183942 | 17847/180/240170/244431 |
| logistic_regression | balanced_mcc | 0.088104 | 0.994600 | 0.711766 | 0.288234 | 0.761031 | 12831/5196/2617/481984 |
| logistic_regression | high_recall | 0.081597 | 0.994903 | 0.681755 | 0.318245 | 0.745296 | 12290/5737/2470/482131 |

Interpretation:

- Threshold choice changes the operational profile substantially.
- For LR, the low-FPR operating point sharply reduces false alarms but misses many attacks.
- For LR, balanced-MCC/high-recall points recover attack recall but increase FPR.
- This supports the thesis trade-off: predictive strength and operational decision quality are separate from proof feasibility.

### 6.2 Calibration

Source: `reports/decision_engineering_baselines.md`.

| Model | Variant | Brier | ECE |
|---|---|---:|---:|
| xgboost | raw | 0.000732 | 0.000271 |
| xgboost | platt | 0.000731 | 0.000174 |
| xgboost | isotonic | 0.000732 | 0.000135 |
| logistic_regression | raw | 0.055734 | 0.121681 |
| logistic_regression | platt | 0.016360 | 0.010188 |
| logistic_regression | isotonic | 0.013126 | 0.000292 |

Interpretation:

- XGBoost is already very well calibrated in this experiment.
- LR raw probabilities are less calibrated; isotonic calibration strongly reduces ECE and Brier.
- Calibration supports decision engineering but does not change the Stage 3.4 circuit claim, which verifies the quantized LR relation.

### 6.3 Cost-Sensitive Thresholds

Source: `reports/cost_based_thresholds.md`.

Use only a compact table in the main text. Put the full FN/FP sweep in the appendix.

| Model | FN/FP ratio | Threshold | Test FPR | Test Recall | Test MCC | Test cost/sample |
|---|---:|---:|---:|---:|---:|---:|
| logistic_regression | 1.0 | 0.088104 | 0.288234 | 0.994600 | 0.761031 | 0.015544 |
| xgboost | 1.0 | 0.489287 | 0.015477 | 0.999639 | 0.986907 | 0.000903 |

Interpretation:

- With equal FN/FP cost, XGBoost remains much stronger.
- LR can be thresholded for high recall, but this comes with substantially higher false-positive rate.

### 6.4 File-Wise Holdout Robustness

Source: `reports/filewise_holdout.md`.

This is a file-wise holdout experiment, not a true timestamp-ordered temporal deployment simulation.

| Point | Threshold | Attack Recall | Normal Recall/Spec | FPR | MCC | Confusion tn/fp/fn/tp |
|---|---:|---:|---:|---:|---:|---|
| default_0.5 | 0.500000 | 0.764417 | 0.904913 | 0.095087 | 0.420292 | 13647/1434/35778/116092 |
| low_fpr | 0.934938 | 0.214914 | 0.991181 | 0.008819 | 0.148739 | 14948/133/119231/32639 |
| balanced_mcc | 0.085572 | 0.979199 | 0.567403 | 0.432597 | 0.613392 | 8557/6524/3159/148711 |
| high_recall | 0.090232 | 0.977573 | 0.568596 | 0.431404 | 0.606608 | 8575/6506/3406/148464 |

Additional setup:

- Held-out files: `Network_dataset_20.csv` to `Network_dataset_23.csv`.
- Holdout rows: 166951.
- Holdout attack rate: 90.9668 percent.
- Per-file sample fraction: 0.05.
- Training cap before validation split: 400000 rows.

Interpretation:

- The experiment addresses the limitation that the main split is stratified random.
- It should be described as source-file robustness, not as temporal validation.
- LR performance degrades under file-wise holdout, especially when high recall is required, which should be presented as mature self-assessment rather than a failure.

### 6.5 Attack-Type Post-Hoc Error Analysis

Source: `reports/final_numbers_source_of_truth.md` and `reports/attack_type_error_analysis.md`.

Use `type` only as post-hoc metadata. It is excluded from training.

| Model | Point | Worst attack type | n | FN | Attack recall | FN rate |
|---|---|---|---:|---:|---:|---:|
| xgboost | default_0.5 | ransomware | 1620 | 173 | 0.893210 | 0.106790 |
| xgboost | balanced_mcc | ransomware | 1620 | 168 | 0.896296 | 0.103704 |
| xgboost | low_fpr | ransomware | 1620 | 344 | 0.787654 | 0.212346 |
| xgboost | high_recall | ransomware | 1620 | 1541 | 0.048765 | 0.951235 |
| logistic_regression | default_0.5 | ransomware | 1620 | 1495 | 0.077160 | 0.922840 |
| logistic_regression | balanced_mcc | ransomware | 1620 | 773 | 0.522840 | 0.477160 |
| logistic_regression | low_fpr | ransomware | 1620 | 1616 | 0.002469 | 0.997531 |
| logistic_regression | high_recall | ransomware | 1620 | 700 | 0.567901 | 0.432099 |

Interpretation:

- Ransomware is consistently the most difficult attack family under the reported operating points.
- This analysis strengthens practical IDS interpretation because it identifies where aggregate binary performance hides errors.
- Do not use this table to alter the main aggregate baseline metrics.

Recommended tables:

- Table 7.2: Operating points and calibration.
- Table 7.3: File-wise holdout and attack-type robustness summary, or split into two smaller tables.

## 7. Semantic Explanation Results

Use in Sections 7.3.1 and 7.3.2.

Source: `reports/stage2_summary.md`.

| Metric | Value | Source |
|---|---:|---|
| Raw feature-level LR stability | 0.5847 | `reports/stage2_summary.md` |
| Raw feature-level XGBoost stability | 0.4075 | `reports/stage2_summary.md` |
| LR-XGBoost raw top-5 overlap mean | 0.1558 | `reports/stage2_summary.md` |
| LR-XGBoost raw top-5 overlap std | 0.0820 | `reports/stage2_summary.md` |
| Semantic LR stability | 0.7794 | `reports/stage2_summary.md` |
| Semantic XGBoost stability | 0.7429 | `reports/stage2_summary.md` |
| LR-XGBoost semantic overlap mean | 0.3012 | `reports/stage2_summary.md` |
| LR-XGBoost semantic overlap std | 0.1468 | `reports/stage2_summary.md` |

Interpretation:

- Semantic grouping improves stability relative to raw feature-level explanations.
- Semantic grouping also improves cross-model overlap, although model disagreement remains.
- This supports using semantic groups as the explanation layer for Stage 3.4.

### Group-Size Bias

Source: `reports/semantic_group_ablation.md`.

| Model | Raw top-3 groups | Size-normalized top-3 groups |
|---|---|---|
| Logistic Regression | Application, Protocol, ConnectionState | Protocol, ConnectionState, Ports |
| XGBoost | TrafficVolume, Ports, Protocol | Ports, Protocol, TrafficVolume |

Interpretation:

- The Application group has 76 features, so raw top-k frequency can overstate its semantic importance.
- Size-normalized analysis shows why raw group frequency must be interpreted carefully.
- This is a good self-assessment point for Chapter 7, but keep the detailed group-size table short.

Recommended table:

- Table 7.4: Raw and semantic explanation stability/overlap.

Recommended optional appendix figure:

- `reports/figures/semantic_group_ablation_logistic_regression.png`
- `reports/figures/semantic_group_ablation_xgboost.png`

## 8. Proxy Attribution versus Semantic-Group Exact SHAP

Use in Section 7.3.3.

Source: `reports/exact_shap_semantic_groups.md`.

### Exact SHAP Configuration

| Item | Value |
|---|---|
| Model | Logistic Regression |
| Value function | LR score/logit, not probability |
| Reference vector | feature-wise training-set mean in processed feature space |
| Subset | `reconstructed_stage2_lr_tp1000_fn100_seed42` |
| Samples | 1100 |
| SHAP players | five semantic groups |
| Exact top-3 rule | descending absolute SHAP value |
| Python tie convention | smaller group ID first |
| Circuit tie rule | non-increasing order only; no deterministic tie-break enforced |

### Group Summary

| Group | Size | Mean abs Exact SHAP | Mean old grouped attribution | Exact top-3 count | Old top-3 count |
|---|---:|---:|---:|---:|---:|
| Protocol | 3 | 1.151115 | 3.059726 | 1044 | 1094 |
| Application | 76 | 0.733157 | 9.164932 | 415 | 1100 |
| ConnectionState | 13 | 1.607628 | 1.641246 | 1061 | 547 |
| Ports | 2 | 0.258602 | 0.286670 | 250 | 80 |
| TrafficVolume | 10 | 0.468695 | 0.904034 | 530 | 479 |

### Agreement Between Old Proxy and Exact SHAP

| Metric | Value |
|---|---:|
| Mean top-3 overlap count | 2.0618 / 3 |
| Mean top-3 Jaccard overlap | 0.5407 |
| Max enumeration-vs-closed-form SHAP difference | 2.842171e-14 |
| Max SHAP additivity residual | 2.842171e-14 |
| Max score reconstruction difference | 1.421085e-14 |

Interpretation:

- The old grouped attribution proxy is cheap and useful as an engineering baseline.
- It is not a Shapley-value explanation.
- Semantic-group Exact SHAP is stronger because it measures marginal contribution relative to an explicit reference vector.
- Stage 3.4 is stronger than Stage 3.3 because it verifies the Exact SHAP top-3 relation rather than the old grouped `sum_i |w_i*x_i|` proxy.
- The old proxy is dominated by Application; Exact SHAP more often emphasizes ConnectionState and Protocol.

Recommended figures:

- `reports/figures/thesis/thesis_figure_06_top3_group_frequency_proxy_vs_exact.png`
- `reports/figures/thesis/thesis_figure_07_top3_overlap_distribution.png`

Recommended table:

- Table 7.5: Old proxy versus Exact SHAP agreement.

## 9. Float-to-Quantized Agreement and Ranking Stability

Use in Section 7.4.

### 9.1 Float LR versus Quantized LR Agreement

Source: `reports/float_vs_quantized_lr_agreement.md`.

| Split | n | Prediction agreement | Mismatches | Mismatch rate | Float attack rate | Quantized attack rate |
|---|---:|---:|---:|---:|---:|---:|
| val | 502628 | 99.991246% | 44 | 0.008754% | 90.498142% | 90.499335% |
| test | 502628 | 99.994230% | 29 | 0.005770% | 90.466707% | 90.465314% |

Score approximation error:

| Split | Mean abs error | p95 abs error | Max abs error |
|---|---:|---:|---:|
| val | 0.040946 | 0.116889 | 161.208082 |
| test | 0.041297 | 0.116913 | 154.911022 |

Exact SHAP top-3 agreement:

| Split | Ordered top-3 match | Ordered mismatches | Mean overlap / 3 | Mean Jaccard |
|---|---:|---:|---:|---:|
| val | 93.855694% | 30883 | 2.945248 | 0.972624 |
| test | 93.817495% | 31075 | 2.944878 | 0.972439 |

Interpretation:

- Prediction agreement is above 99.99 percent on both validation and test splits.
- The ZK proof remains a proof of the integer circuit relation, not a cryptographic proof that the integer relation equals the floating-point model for all possible inputs.
- Prediction mismatches should be treated as quantization boundary effects.
- Ordered top-3 agreement is lower than prediction agreement because group rankings can change when margins are small, even if the unordered overlap remains high.

### 9.2 Exact SHAP Ranking Margin

Source: `reports/exact_shap_ranking_margin.md`.

Margin definition:

```text
margin = abs(phi_rank3_int) - abs(phi_rank4_int)
margin_scaled = margin / (Sx * Sw)
```

| Split | n | min | p1 | p5 | p10 | median | mean | p95 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| val | 502628 | 1.274049e-06 | 0.000411 | 0.000411 | 0.000411 | 0.044013 | 0.166426 | 0.774113 | 1.907891 |
| test | 502628 | 1.274049e-06 | 0.000411 | 0.000411 | 0.000411 | 0.044013 | 0.167759 | 0.774113 | 5.073528 |

Small-margin counts:

| Split | <=0 | <=0.001 | <=0.01 | <=0.1 | <=1.0 |
|---|---:|---:|---:|---:|---:|
| val | 0 (0.0000%) | 56155 (11.1723%) | 134680 (26.7952%) | 340658 (67.7754%) | 500513 (99.5792%) |
| test | 0 (0.0000%) | 55692 (11.0802%) | 134761 (26.8113%) | 339205 (67.4863%) | 500522 (99.5810%) |

Interpretation:

- Stage 3.4 certifies that the public top-3 ranking is correct for the supplied private input under the quantized relation.
- It does not certify ranking robustness under nearby inputs, alternative references, or quantization perturbations.
- Near-zero rank-3/rank-4 margins explain why ordered top-3 agreement is lower than prediction agreement.
- This is an important self-assessment result for grade-5-level maturity.

Recommended table:

- Table 7.6: Float-to-quantized prediction/top-3 agreement and ranking-margin statistics.

## 10. ZK Correctness and Negative Tests

Use in Section 7.5.1.

Source: `reports/stage34_thesis_integration.md` and `stage3_zk/reports/STAGE34_PROOF_REPORT.md`.

Correctness evidence:

- Python coalition enumeration equals closed-form LR Exact SHAP: max difference `2.842171e-14`.
- Stage 3.4 valid witnesses pass for samples 1-8.
- Stage 3.4 Groth16 proof generation and verification pass for samples 1-8.
- Supplemental Stage 3.4 batch smoke test passes for 30 deterministic label-balanced test rows: 30 witness passes, 30 proof passes, 30 verification passes, and 30 public-output matches.
- Stage 3.4 negative witness tests reject malformed inputs for samples 1-8.
- Stage 3.4 binds `y_hat` and ordered non-increasing top-3 group IDs to the same private shifted input vector.

Use the 30-sample batch only as supporting functional evidence. It is not a statistical proof-reliability estimate and does not replace the authoritative proof-cost timings from the eight curated vectors.

Negative-test categories:

| Test category | Expected result | Source |
|---|---|---|
| wrong `y_hat` | rejected | `reports/stage34_thesis_integration.md` |
| wrong Exact SHAP top-3 IDs | rejected | `reports/stage34_thesis_integration.md` |
| duplicate group IDs | rejected | `reports/stage34_thesis_integration.md` |
| out-of-range group IDs | rejected | `reports/stage34_thesis_integration.md` |
| malicious `other2_ids` reusing top groups | rejected | `reports/stage34_thesis_integration.md` |
| private input range violation | rejected | `reports/stage34_thesis_integration.md` |

Important interpretation:

- Proof correctness means consistency with the public model, private witness, fixed reference vector, and public top-3 claim.
- It does not mean the model prediction equals the ground-truth label.
- The false-negative case study is useful because it makes this distinction clear.

Recommended table:

- Table 7.7: Stage 3.4 proof-correctness and negative-test summary.

## 11. Circuit Complexity and Proof Cost

Use in Section 7.5.2.

Source: `stage3_zk/reports/STAGE34_PROOF_REPORT.md`.

### Stage 3.4 Circuit Statistics

| Metric | Value |
|---|---:|
| Constraints | 8358 |
| Wires | 8078 |
| Public inputs | 109 |
| Private inputs | 106 |
| Labels | 9459 |
| Outputs | 0 |

Artifact sizes:

| Artifact | Bytes |
|---|---:|
| R1CS | 1283048 |
| WASM | 99582 |
| ZKey | 4573072 |
| Verification key | 22669 |

Proof timings and sizes over samples 1-8:

| Metric | Value |
|---|---:|
| Witness time | 58-72 ms, mean 63 ms |
| Prove time | 1009-1365 ms, mean 1144 ms |
| Verify time | 618-915 ms, mean 701 ms |
| Proof size | 800-807 bytes, mean 804 bytes |
| Public bytes | 1178 bytes |

Individual proof results:

| Sample | Witness ms | Prove ms | Verify ms | Proof bytes | Public bytes | Public signals | Status |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 64 | 1280 | 711 | 805 | 1178 | 109 | PASS |
| 2 | 58 | 1248 | 817 | 800 | 1178 | 109 | PASS |
| 3 | 63 | 1009 | 630 | 806 | 1178 | 109 | PASS |
| 4 | 65 | 1365 | 915 | 807 | 1178 | 109 | PASS |
| 5 | 72 | 1102 | 618 | 802 | 1178 | 109 | PASS |
| 6 | 60 | 1085 | 618 | 806 | 1178 | 109 | PASS |
| 7 | 59 | 1029 | 639 | 805 | 1178 | 109 | PASS |
| 8 | 61 | 1033 | 657 | 805 | 1178 | 109 | PASS |

Interpretation:

- These are local CLI prototype timings, not hardware-independent guarantees.
- Stage 3.4 is practical for prototype-scale evaluation.
- Do not claim production readiness.

Recommended figures:

- `reports/figures/thesis/thesis_figure_04_constraints_by_stage.png`
- `reports/figures/thesis/thesis_figure_05_prove_verify_time_by_stage.png`

Recommended table:

- Table 7.8: Stage 3.4 circuit size and proof cost.

## 12. Case Studies and Diverse Test Vectors

Use in Section 7.5.3.

### 12.1 Original Case Studies

Source: `reports/stage34_case_studies.md`.

| Sample | Label | y_true | y_hat | Stage 3.3 old top-3 | Stage 3.4 Exact SHAP top-3 | Proof |
|---:|---|---:|---:|---|---|---|
| 1 | TP_attack | 1 | 1 | Application, Protocol, TrafficVolume | Application, ConnectionState, Protocol | PASS |
| 2 | TN_normal | 0 | 0 | Application, ConnectionState, Protocol | ConnectionState, Protocol, TrafficVolume | PASS |
| 3 | FN_attack | 1 | 0 | Application, Protocol, TrafficVolume | Protocol, Application, ConnectionState | PASS |

Interpretation:

- Sample 1 shows a true-positive attack where prediction and explanation both verify.
- Sample 2 shows a true-negative normal sample where Exact SHAP differs meaningfully from the old proxy.
- Sample 3 shows a false-negative attack, demonstrating that the proof verifies model computation and explanation authenticity, not ground-truth correctness.

### 12.2 Diverse Stage 3.4 Vectors

Source: `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md`.

| Stage 3.4 sample | Label | Test row | Dataset index | y_true | y_hat | score_int | abs(score) | top-3 groups | rank3-rank4 margin |
|---:|---|---:|---:|---:|---:|---:|---:|---|---:|
| 4 | FP_normal | 206297 | 2037930 | 0 | 1 | 23752516133 | 23752516133 | TrafficVolume, Protocol, ConnectionState | 291043568 |
| 5 | HighConf_attack | 199211 | 497442 | 1 | 1 | 46656741774 | 46656741774 | TrafficVolume, ConnectionState, Protocol | 117262245 |
| 6 | HighConf_normal | 497400 | 1714021 | 0 | 0 | -67272542694 | 67272542694 | TrafficVolume, ConnectionState, Application | 132364379 |
| 7 | Borderline_score | 19818 | 583370 | 1 | 0 | -133791 | 133791 | Application, TrafficVolume, ConnectionState | 29012299 |
| 8 | SmallTop3Margin | 266195 | 1406019 | 1 | 1 | 755662630 | 755662630 | ConnectionState, Protocol, Ports | 342 |

Interpretation:

- `FP_normal` tests proof correctness when the model predicts Attack for a Normal row.
- High-confidence attack/normal cases test large positive and negative score margins.
- `Borderline_score` tests a prediction close to the LR decision boundary.
- `SmallTop3Margin` tests a near tie between rank 3 and rank 4.
- These are correctness/stress vectors, not additional training data.

Recommended figure:

- `reports/figures/thesis/thesis_figure_08_case_study_group_bars.png` if there is space; otherwise use tables only.

## 13. Output Leakage and Reference Sensitivity

Use in Sections 7.6.1 and 7.6.2.

### 13.1 Output Leakage

Source: `reports/stage34_output_leakage_audit.md`.

Stage 3.4 intentionally reveals the binary prediction and ordered top-3 semantic group IDs.

| Metric | Value |
|---|---:|
| Samples audited | 1100 |
| Predicted-label entropy | 0.4395 bits |
| Exact top-3 sequence entropy | 2.9615 bits |
| Unique Exact SHAP top-3 sequences | 22 / 60 |

Public prediction distribution:

| Predicted label | Count | Rate |
|---:|---:|---:|
| 0 | 100 | 9.09% |
| 1 | 1000 | 90.91% |

Most common group membership in top-3:

| Group | Count in top-3 | Rate |
|---|---:|---:|
| Protocol | 1044 | 94.91% |
| Application | 415 | 37.73% |
| ConnectionState | 1061 | 96.45% |
| Ports | 250 | 22.73% |
| TrafficVolume | 530 | 48.18% |

Interpretation:

- The system provides input-feature privacy with intentional output disclosure.
- It does not provide complete behavioral secrecy.
- It does not provide differential privacy because no noise is added to `y_hat` or top-3 IDs.

### 13.2 Reference Sensitivity

Source: `reports/exact_shap_reference_sensitivity.md`.

The implemented Stage 3.4 circuit verifies the training-mean reference only. Alternative references are offline sensitivity checks.

| Reference | Mean overlap / 3 | Mean Jaccard | Ordered top-3 changed | Changed rate |
|---|---:|---:|---:|---:|
| zero_vector | 2.2736 | 0.6399 | 1012 | 92.00% |
| normal_train_mean | 2.3945 | 0.6973 | 865 | 78.64% |

Interpretation:

- Exact SHAP explanations depend strongly on the reference vector.
- The training-mean reference remains the only verified circuit reference.
- This belongs in self-assessment, not as a new ZK claim.

Recommended table:

- Table 7.9: Output leakage and reference sensitivity summary.

## 14. Optional Stage 3.5 Input-Commitment Appendix Result

Use in Section 7.6.3 only if Chapter 7 includes appendix-level evidence. Keep it short.

Source: `reports/input_commitment_appendix.md` and `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md`.

### 14.1 Status and Meaning

Stage 3.5 computes a public Poseidon rolling commitment over:

```text
(domain_tag, metadata_hash, salt, x_shifted[104])
```

Public values:

- `metadata_hash`
- `input_commitment`
- `y_hat`
- `top3_ids`

Private values:

- `salt`
- `x_shifted[104]`
- `other2_ids`

Interpretation:

- Stage 3.5 demonstrates a feasible commitment binding point.
- It does not provide full SIEM provenance by itself.
- A real deployment still needs a trusted ingestion-time commitment registry, metadata schema, replay policy, and trust model.

### 14.2 Circuit Delta and Timing

| Metric | Stage 3.4 | Stage 3.5 Prototype |
|---|---:|---:|
| Constraints | 8358 | 25094 |
| Wires | 8078 | 24816 |
| Public inputs | 109 | 110 |
| Private inputs | 106 | 107 |
| Outputs | 0 | 1 |

Constraint overhead versus Stage 3.4: 3.0x.

Artifact sizes:

| Artifact | Bytes |
|---|---:|
| R1CS | 4236604 |
| WASM | 4174756 |
| ZKey | 11408750 |
| Verification key | 23052 |

Proof results:

| Sample | Witness ms | Prove ms | Verify ms | Tampered commitment rejected | Public signals | Proof bytes |
|---:|---:|---:|---:|---|---:|---:|
| 1 | 541 | 2217 | 690 | yes | 111 | 806 |
| 7 | 399 | 2972 | 1647 | yes | 111 | 807 |
| 8 | 817 | 3002 | 786 | yes | 111 | 803 |

Timing summary:

| Metric | Stage 3.4 Mean | Stage 3.5 Mean |
|---|---:|---:|
| Witness ms | 62.8 | 585.7 |
| Prove ms | 1143.9 | 2730.3 |
| Verify ms | 700.6 | 1041.0 |

Recommended wording:

- "Stage 3.5 is treated as appendix-level feasibility evidence."
- "The prototype closes the narrow 'some private witness' gap only when an external registry stores the same public commitment at ingestion time."
- "Because of its scope and overhead, it is not used as the main claim."

## 15. Verifier Policy and Model Binding

Use briefly in Sections 7.5 or 7.6 if needed.

Source: `reports/model_registry_and_verifier_policy.md`.

Verifier acceptance conditions:

1. The verification key corresponds to the approved Stage 3.4 circuit version.
2. Public weights and bias match the approved `model_public.json`.
3. Feature order, semantic group map, quantization configuration, and Exact SHAP reference vector match approved artifacts.
4. The approved artifact digest or model identifier matches the registered model version.
5. The Groth16 proof verifies.
6. Public `y_hat` and `top3_ids` are interpreted as certified prediction and semantic explanation.

Current approved Stage 3.4 combined digest:

```text
6c3c9e086aceb1f2a0038c1c3726baf49998a310fcd64421b98cadaf39e32b14
```

Interpretation:

- This is model binding, not model confidentiality.
- The verifier knows the model and checks that it is the approved public model version.
- Hidden-model commitment is future work.

## 16. Recommended Tables and Figures

### Main-Text Tables

Use a compact table set in Chapter 7. Some evidence blocks above contain more detailed tables; the thesis should merge or shorten them where possible so the chapter reads like an evaluation narrative rather than a report dump.

| Proposed table | Chapter location | Content | Source |
|---|---|---|---|
| Table 7.1 | 7.2.1 | Baseline IDS performance | `reports/baseline_extended_metrics.md` |
| Table 7.2 | 7.2.2 | Operating points and calibration | `reports/decision_engineering_baselines.md` |
| Table 7.3 | 7.2.3 | Robustness checks: file-wise holdout and attack-type errors | `reports/filewise_holdout.md`, `reports/attack_type_error_analysis.md` |
| Table 7.4 | 7.3 | Explanation behaviour: stability, group-size bias, proxy-vs-Exact SHAP | `reports/stage2_summary.md`, `reports/semantic_group_ablation.md`, `reports/exact_shap_semantic_groups.md` |
| Table 7.5 | 7.4 | ML-to-ZK validity: quantized agreement and ranking margins | `reports/float_vs_quantized_lr_agreement.md`, `reports/exact_shap_ranking_margin.md` |
| Table 7.6 | 7.5 | Stage 3.4 proof evaluation: correctness, negative tests, circuit cost | `reports/stage34_thesis_integration.md`, `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |
| Table 7.7 | 7.5.3 | Case studies and diverse test vectors | `reports/stage34_case_studies.md`, `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md` |
| Table 7.8 | 7.6 | Leakage, reference sensitivity, and optional commitment summary | `reports/stage34_output_leakage_audit.md`, `reports/exact_shap_reference_sensitivity.md`, `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md` |

Optional appendix tables:

| Proposed appendix table | Content | Source |
|---|---|---|
| Appendix table | Stage 3.5 input commitment | `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md` |
| Appendix table | Full cost-ratio sweep | `reports/cost_based_thresholds.md` |

### Main-Text Figures

For Chapter 7, the most relevant figures are:

| Figure file | Use |
|---|---|
| `reports/figures/thesis/thesis_figure_04_constraints_by_stage.png` | Circuit complexity progression |
| `reports/figures/thesis/thesis_figure_05_prove_verify_time_by_stage.png` | Proof overhead progression |
| `reports/figures/thesis/thesis_figure_06_top3_group_frequency_proxy_vs_exact.png` | Old proxy vs Exact SHAP behavior |
| `reports/figures/thesis/thesis_figure_07_top3_overlap_distribution.png` | Old proxy vs Exact SHAP overlap |
| `reports/figures/thesis/thesis_figure_08_case_study_group_bars.png` | Optional case-study explanation bars |

Use ML ROC/PR/reliability figures only in the appendix unless Chapter 7 has extra space:

- `reports/figures/decision_engineering_*_roc.png`
- `reports/figures/decision_engineering_*_pr.png`
- `reports/figures/decision_engineering_*_reliability_*.png`

The FPR-vs-recall figures are the most useful ML figures if one ML curve is needed:

- `reports/figures/decision_engineering_xgboost_fpr_vs_recall.png`
- `reports/figures/decision_engineering_logistic_regression_fpr_vs_recall.png`

## 17. Main-Text versus Appendix Guidance

Keep in main Chapter 7:

- baseline metrics;
- operating points and calibration summary;
- file-wise holdout summary;
- attack-type worst false-negative family summary;
- semantic stability and group-size bias;
- proxy vs Exact SHAP agreement;
- float-vs-quantized agreement;
- ranking-margin self-assessment;
- Stage 3.4 proof correctness, negative tests, and proof cost;
- diverse test vectors;
- output leakage summary;
- short reference-sensitivity paragraph.

Move to appendix or mention briefly:

- full cost-sensitive threshold sweep;
- detailed calibration plots;
- ROC/PR curves;
- full output leakage ordered-sequence distribution;
- full reference-sensitivity group-frequency table;
- Stage 3.5 detailed proof table;
- historical Stage 3.1-3.3 proof outputs if Chapter 6 already covered circuit progression.

## 18. RQ Mapping for Section 7.7

Use this mapping in the chapter summary.

| RQ | Evidence |
|---|---|
| RQ1: Can public linear/logistic tabular inference be verified without revealing processed IDS features? | Stage 3.4 proof generation/verification for samples 1-8; supplemental 30-sample batch smoke test; private `x_shifted[104]`; proof cost table. |
| RQ2: Can semantic explanations be verified rather than trusted as client-supplied metadata? | Negative tests reject wrong top-3 IDs, duplicate IDs, out-of-range IDs, malicious `other2_ids`; Stage 3.4 verifies ordered top-3 semantic-group IDs. |
| RQ3: Can semantic-group Exact SHAP be made feasible in a SNARK for public Logistic Regression? | Closed-form LR Exact SHAP residuals near zero; Stage 3.4 constraints 8358; prove mean 1144 ms; verify mean 701 ms. |
| RQ4: What overhead and limitations arise when moving from proxy attribution to verified Exact SHAP? | Proxy-vs-Exact overlap 2.0618/3; quantized agreement >99.99 percent for prediction but 93.8 percent ordered top-3; ranking-margin fragility; output leakage; fixed reference sensitivity. |

## 19. Suggested Chapter 7 Opening Claim

Useful framing sentence:

```text
Chapter 7 evaluates whether the implemented system supports the claims formalized in Chapter 6: that a public Logistic Regression IDS decision and a semantic-group Exact SHAP top-3 explanation can be verified under private input, while keeping the limitations of the proof-compatible model, quantization, output disclosure, and deployment provenance explicit.
```

## 20. Prompt to Give ChatGPT for Drafting

Use this after attaching this evidence pack and, if possible, `reports/final_numbers_source_of_truth.md`.

```text
Write Chapter 7: Evaluation and Results for my Master's thesis.

Use only the provided evidence pack and source files. Do not invent numbers or claims.
If a value is missing, write [TODO: insert value].

Important scope:
- Main claim: public-model/private-input verification for a public Logistic Regression IDS model.
- Main implementation: Stage 3.4 verifies public y_hat and ordered top-3 semantic-group Exact SHAP IDs from the same private x_shifted[104] witness.
- Stage 3.5 input commitment is appendix-only feasibility evidence, not the main claim.

Do not claim model confidentiality, model-agnostic SHAP, XGBoost-in-ZK, differential privacy, full SIEM provenance, Partition SHAP, sumcheck/GKR, or production readiness.

Use this compact Chapter 7 structure:

7.1 Evaluation Setup

7.2 IDS Performance and Decision Behaviour
    7.2.1 Baseline Detection Performance
    7.2.2 Threshold Selection and Calibration
    7.2.3 Robustness and Attack-Type Error Analysis

7.3 Explanation Behaviour
    7.3.1 Raw and Semantic Explanation Stability
    7.3.2 Group-Size Bias
    7.3.3 Proxy Attribution versus Semantic-Group Exact SHAP

7.4 ML-to-ZK Validity
    7.4.1 Float-to-Quantized Logistic Regression Agreement
    7.4.2 Exact SHAP Top-3 Agreement
    7.4.3 Ranking-Margin Analysis

7.5 Zero-Knowledge Proof Evaluation
    7.5.1 Stage 3.4 Correctness and Negative Tests
    7.5.2 Circuit Complexity and Proof Cost
    7.5.3 Diverse Test Vectors and Case Studies

7.6 Privacy, Leakage, and Scope Boundaries
    7.6.1 Public Output Leakage
    7.6.2 Reference Sensitivity
    7.6.3 Optional Input-Commitment Prototype

7.7 Summary of Findings

The evidence blocks in the evidence pack are source blocks, not chapter sections. Fold them into the structure above.

Write in clear academic English. Avoid first person. Do not overuse bullet points. Each table/figure must be introduced and interpreted. Use source values exactly. Keep Stage 3.5 short and appendix-level.

First produce a refined Chapter 7 outline with recommended tables and figures using the compact structure above. Then write only the Chapter 7 opening and Section 7.1 Evaluation Setup. Wait for confirmation before writing Section 7.2.
```
