# Final Numbers Source of Truth

Generated: 2026-06-19T01:33:15+00:00 (UTC)

Use this file as the checklist for final thesis tables. Older benchmark artifacts may remain useful as historical optimization notes, but final claims should cite the source files listed here.

## Authoritative Files

| Topic | Use this source | Notes |
|---|---|---|
| Baseline ML metrics | `reports/baseline_extended_metrics.md` / `outputs/reports/baseline_metrics_extended.json` | Main test-set classification table. |
| Operating points and calibration | `reports/decision_engineering_baselines.md` / `outputs/reports/decision_engineering_baselines.json` | Low-FPR, balanced-MCC, high-recall thresholds. |
| Cost-sensitive thresholds | `reports/cost_based_thresholds.md` / `outputs/reports/cost_based_thresholds.json` | FN/FP cost-ratio sweep. |
| File-wise holdout robustness | `reports/filewise_holdout.md` / `outputs/reports/filewise_holdout.json` | Train on earlier-numbered files, evaluate on held-out later files. |
| Attack-type error analysis | `reports/attack_type_error_analysis.md` / `outputs/reports/attack_type_error_analysis.json` | Post-hoc false-negative analysis using `type` metadata only after prediction. |
| ML-to-ZK quantization agreement | `reports/float_vs_quantized_lr_agreement.md` / `outputs/reports/float_vs_quantized_lr_agreement.json` | Float sklearn LR vs integer LR relation. |
| Exact SHAP ranking margin | `reports/exact_shap_ranking_margin.md` / `outputs/reports/exact_shap_ranking_margin.json` | Rank-3 vs rank-4 margin self-assessment. |
| Stage 3.1-3.3 ZK evidence | `stage3_zk/reports/LATEST_REPRO_REPORT.md` | Current general ZK harness report. |
| Stage 3.4 proof evidence | `stage3_zk/reports/STAGE34_PROOF_REPORT.md` | Exact SHAP circuit after WSL Circom rebuild and forced setup. |
| Stage 3.4 diverse test vectors | `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md` / `stage3_zk/test_vectors/test_sample_4.json`-`test_sample_8.json` | FP, high-confidence, borderline, and near-tie cases. |
| Stage 3.4 verifier policy | `reports/model_registry_and_verifier_policy.md` and `stage3_zk/artifacts/model_registry_stage34.json` | Registry digest and model binding. |
| Stage 3.5 input-commitment appendix | `reports/input_commitment_appendix.md` / `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md` | Appendix-only provenance binding prototype; not part of the main Stage 3.4 claim. |

## Baseline Classification Metrics

Test-set metrics from `baseline_metrics_extended.json`.

| Model | Operating point | Threshold | Balanced Acc | MCC | Attack Recall | Normal Recall/Spec | FPR | Confusion tn/fp/fn/tp |
|---|---|---:|---:|---:|---:|---:|---:|---|
| xgboost | default_0.5 | 0.500000 | 0.992132 | 0.986851 | 0.999631 | 0.984634 | 0.015366 | 17750/277/179/484422 |
| xgboost | tuned_mcc | 0.489287 | 0.992081 | 0.986907 | 0.999639 | 0.984523 | 0.015477 | 17748/279/175/484426 |
| xgboost | tuned_bacc | 0.968393 | 0.996811 | 0.955497 | 0.996729 | 0.996894 | 0.003106 | 17971/56/1585/483016 |
| logistic_regression | default_0.5 | 0.500000 | 0.923103 | 0.535818 | 0.935017 | 0.911189 | 0.088811 | 16426/1601/31491/453110 |
| logistic_regression | tuned_mcc | 0.088104 | 0.853183 | 0.761031 | 0.994600 | 0.711766 | 0.288234 | 12831/5196/2617/481984 |
| logistic_regression | tuned_bacc | 0.620204 | 0.929770 | 0.538253 | 0.933095 | 0.926444 | 0.073556 | 16701/1326/32422/452179 |

## Operating Points

Thresholds chosen on validation and evaluated on test, from `decision_engineering_baselines.json`.

| Model | Point | Threshold | Attack Recall | Normal Recall/Spec | FPR | MCC | Confusion tn/fp/fn/tp |
|---|---|---:|---:|---:|---:|---:|---|
| xgboost | low_fpr | 0.807750 | 0.999226 | 0.991124 | 0.008876 | 0.984716 | 17867/160/375/484226 |
| xgboost | balanced_mcc | 0.489287 | 0.999639 | 0.984523 | 0.015477 | 0.986907 | 17748/279/175/484426 |
| xgboost | high_recall | 0.984017 | 0.994868 | 0.997615 | 0.002385 | 0.933712 | 17984/43/2487/482114 |
| logistic_regression | low_fpr | 0.938810 | 0.504396 | 0.990015 | 0.009985 | 0.183942 | 17847/180/240170/244431 |
| logistic_regression | balanced_mcc | 0.088104 | 0.994600 | 0.711766 | 0.288234 | 0.761031 | 12831/5196/2617/481984 |
| logistic_regression | high_recall | 0.081597 | 0.994903 | 0.681755 | 0.318245 | 0.745296 | 12290/5737/2470/482131 |

## Cost-Sensitive Thresholds

Use `reports/cost_based_thresholds.md` for the full FN/FP sweep. Key ratio 1.0 rows are listed here.

| Model | FN/FP ratio | Threshold | Test FPR | Test Recall | Test MCC | Test cost/sample |
|---|---:|---:|---:|---:|---:|---:|
| logistic_regression | 1.0 | 0.088104 | 0.288234 | 0.994600 | 0.761031 | 0.015544 |
| xgboost | 1.0 | 0.489287 | 0.015477 | 0.999639 | 0.986907 | 0.000903 |

## ML-to-ZK Quantization Agreement

Float sklearn LR vs Stage 3 integer LR relation, from `float_vs_quantized_lr_agreement.json`.

| Split | n | Prediction agreement | Mismatches | Ordered Exact SHAP top-3 match | Mean top-3 overlap / 3 |
|---|---:|---:|---:|---:|---:|
| val | 502628 | 99.991246% | 44 | 93.855694% | 2.945248 |
| test | 502628 | 99.994230% | 29 | 93.817495% | 2.944878 |

## Exact SHAP Ranking Margin

Rank-3 vs rank-4 margin for the verified quantized Exact SHAP relation.

| Split | n | min margin | p5 margin | median margin | <=0.001 rate | <=0.01 rate |
|---|---:|---:|---:|---:|---:|---:|
| val | 502628 | 0.000001 | 0.000411 | 0.044013 | 11.172279% | 26.795165% |
| test | 502628 | 0.000001 | 0.000411 | 0.044013 | 11.080163% | 26.811280% |

## File-wise Holdout Robustness

Supplementary robustness check from `filewise_holdout.json`. This is a file-wise split by source CSV number, not a true timestamp-ordered temporal deployment simulation.

- Held-out files: `Network_dataset_20.csv, Network_dataset_21.csv, Network_dataset_22.csv, Network_dataset_23.csv`
- Sample fraction: `0.05`, train/val cap: `400000`, holdout n: `166951`, holdout attack rate: `90.9668%`.

| Point | Threshold | Attack Recall | Normal Recall/Spec | FPR | MCC | Confusion tn/fp/fn/tp |
|---|---:|---:|---:|---:|---:|---|
| default_0.5 | 0.500000 | 0.764417 | 0.904913 | 0.095087 | 0.420292 | 13647/1434/35778/116092 |
| low_fpr | 0.934938 | 0.214914 | 0.991181 | 0.008819 | 0.148739 | 14948/133/119231/32639 |
| balanced_mcc | 0.085572 | 0.979199 | 0.567403 | 0.432597 | 0.613392 | 8557/6524/3159/148711 |
| high_recall | 0.090232 | 0.977573 | 0.568596 | 0.431404 | 0.606608 | 8575/6506/3406/148464 |

## Attack-Type Error Analysis

`type` is excluded from training and used only as post-hoc metadata. Rows below show the highest-FN-rate attack type for each model and operating point among attack types meeting the report support threshold.

- Metadata/test label alignment mismatches: `0`.
- Minimum attack-type support: `100` true attack rows.

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

## Stage 3.4 Exact SHAP Proof Evidence

| Metric | Value | Source |
|---|---:|---|
| Constraints | 8358 | `STAGE34_PROOF_REPORT.md` |
| Wires | 8078 | `STAGE34_PROOF_REPORT.md` |
| Public inputs | 109 | `STAGE34_PROOF_REPORT.md` |
| Private inputs | 106 | `STAGE34_PROOF_REPORT.md` |
| R1CS bytes | 1283048 | `STAGE34_PROOF_REPORT.md` |
| WASM bytes | 99582 | `STAGE34_PROOF_REPORT.md` |
| ZKey bytes | 4573072 | `STAGE34_PROOF_REPORT.md` |
| Verification key bytes | 22669 | `STAGE34_PROOF_REPORT.md` |
| Witness ms, samples 1-8 | 58-72 (mean 63) | `STAGE34_PROOF_REPORT.md` |
| Prove ms, samples 1-8 | 1009-1365 (mean 1144) | `STAGE34_PROOF_REPORT.md` |
| Verify ms, samples 1-8 | 618-915 (mean 701) | `STAGE34_PROOF_REPORT.md` |
| Proof bytes, samples 1-8 | 800-807 (mean 804) | `STAGE34_PROOF_REPORT.md` |
| Public bytes, samples 1-8 | 1178-1178 (mean 1178) | `STAGE34_PROOF_REPORT.md` |

## Stage 3.4 Registry Digest

- Current approved combined digest: `f31ed43b8b872fc71e917243441ff5c130acb1384e9f7ef46f638dd32a0858e7`
- Policy verifier: `python tools/verify_stage34_policy.py --self-test` and `python tools/verify_stage34_policy.py`.
- Do not mix this digest with older verification keys or pre-rebuild Stage 3.4 reports.

## Stage 3.5 Input-Commitment Appendix

Appendix-only evidence from `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md`. This prototype adds a public Poseidon commitment to the private input witness and simulated event metadata. It demonstrates feasibility of a commitment check, but full provenance still requires an external trusted commitment registry.

| Metric | Value | Source |
|---|---:|---|
| Constraints | 25094 | `STAGE35_INPUT_COMMITMENT_REPORT.md` |
| Wires | 24816 | `STAGE35_INPUT_COMMITMENT_REPORT.md` |
| Public inputs | 110 | `STAGE35_INPUT_COMMITMENT_REPORT.md` |
| Private inputs | 107 | `STAGE35_INPUT_COMMITMENT_REPORT.md` |
| Public outputs | 1 | `STAGE35_INPUT_COMMITMENT_REPORT.md` |
| Constraint overhead vs Stage 3.4 | 3.0x | `STAGE35_INPUT_COMMITMENT_REPORT.md` |
| Witness ms, samples 1,7,8 | 399-817 (mean 586) | `STAGE35_INPUT_COMMITMENT_REPORT.md` |
| Prove ms, samples 1,7,8 | 2217-3002 (mean 2730) | `STAGE35_INPUT_COMMITMENT_REPORT.md` |
| Verify ms, samples 1,7,8 | 690-1647 (mean 1041) | `STAGE35_INPUT_COMMITMENT_REPORT.md` |
| Tampered public commitment | rejected for samples 1, 7, 8 | `STAGE35_INPUT_COMMITMENT_REPORT.md` |

## Historical Or Appendix-Only Numbers

- Older Node API timing artifacts under `stage3_zk/outputs/proofs/` and `stage3_zk/reports/bench/` should be labelled historical if cited.
- `stage3_zk/reports/STAGE34_EXACT_SHAP_SUMMARY.md` is an implementation status summary; use `STAGE34_PROOF_REPORT.md` for current proof timings.
- Stage 3.5 input commitment numbers are appendix-only; cite them as a feasibility prototype, not as the main system baseline.
- `drift_chunks.md` is a drift/robustness proxy over ordered random-test chunks, not a true temporal holdout.
- `filewise_holdout.md` is a source-file robustness check; cite it as file-wise holdout, not timestamp validation.
