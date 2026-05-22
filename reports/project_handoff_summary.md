# ZK-XIDS Project Handoff Summary

Tai lieu nay tom tat repo **ZK-XIDS: Zero-Knowledge Privacy-Preserving Intrusion Detection System** de mot ben thu ba co the doc nhanh, hieu dung project, tai lap ket qua can thiet, va de xuat them scope cho thesis.

Ngay tao tai lieu: 2026-05-21  
Nguon chinh: `README.md`, `reports/*.md`, `stage3_zk/reports/*.md`, va mot so file cau hinh trong repo.

## 1. Executive Summary

Project nay xay dung mot he thong IDS bao ve quyen rieng tu tren dataset TON_IoT Network. Pipeline gom 3 phan lon:

1. **ML intrusion detection**: xu ly du lieu, chia train/validation/test, train baseline Logistic Regression va XGBoost cho bai toan binary classification `Normal` vs `Attack`.
2. **Explainability**: tao giai thich top-k theo feature, sau do gom 104 features thanh 5 semantic groups de explanation on dinh va de hieu hon.
3. **Zero-Knowledge proof**: dung Circom + Groth16 de prover chung minh rang du doan va top-3 semantic explanation la dung theo model da cong bo, nhung khong tiet lo raw network traffic features.

Thong diep thesis manh nhat:

> ZK-XIDS cho phep mot client chung minh voi SOC/verifier rang mot mau network traffic duoc phan loai dung boi IDS model va top-3 semantic explanation la that, trong khi van giu kin input features.

## 2. Problem Statement

Trong moi truong SOC hoac multi-tenant security monitoring, client co the khong muon chia se raw network traffic vi ly do privacy, compliance, hoac business confidentiality. Tuy nhien SOC can tin rang:

- Ket qua phan loai `Attack`/`Normal` la dung theo model da thoa thuan.
- Explanation khong bi client gia mao de danh lac huong dieu tra.
- Qua trinh verify nhanh va nhe hon prover.

Project giai quyet bai toan nay bang cach ket hop:

- IDS model cho network intrusion detection.
- Explainable AI o muc semantic group.
- ZK-SNARK proof cho correctness va explanation authenticity.

## 3. Repository Map

Nhung file nen doc dau tien:

- [`README.md`](../README.md): tong quan repo va quickstart.
- [`reports/thesis_project_map.md`](thesis_project_map.md): ban do thesis-oriented, rat quan trong.
- [`reports/dataset_summary.md`](dataset_summary.md): Stage 1 dataset, split, leakage control.
- [`reports/stage2_summary.md`](stage2_summary.md): Stage 2 top-k explainability.
- [`stage3_zk/reports/FINAL_SUMMARY.md`](../stage3_zk/reports/FINAL_SUMMARY.md): narrative Stage 3.
- [`stage3_zk/reports/LATEST_REPRO_REPORT.md`](../stage3_zk/reports/LATEST_REPRO_REPORT.md): evidence report moi nhat, nen dung lam source of truth cho ZK constraints, artifact sizes, prove/verify status.
- [`reports/README.md`](README.md): index cac reports va figures.

Thu muc chinh:

| Path | Vai tro |
|---|---|
| `data/` | Raw va processed TON_IoT datasets |
| `notebooks/` | Notebook pipeline tu data sanity check den export ZK artifacts |
| `outputs/` | ML artifacts: splits, processed arrays, models, reports, Stage 2 outputs |
| `reports/` | Markdown reports cho Stage 1/2 va ML evaluation |
| `tools/` | Script-first reproducibility va evaluation suite |
| `stage3_zk/` | Circom circuits, ZK scripts, artifacts, proofs, reports |

## 4. Stage 1: Dataset, Split, Preprocessing

Nguon du lieu: TON_IoT processed network dataset.

Dataset mode duoc ghi nhan trong reports:

- Mode: `processed_stratified_sample_23files_frac0.15`
- Sample fraction: `15%` moi file trong 23 processed CSV shards
- Total samples: `3,350,853`
- Total columns loaded: `47`
- Label target: binary `label`, voi `0 = Normal`, `1 = Attack`

Label distribution:

| Class | Count | Percentage |
|---|---:|---:|
| Normal | 119,481 | 3.57% |
| Attack | 3,231,372 | 96.43% |

Split strategy:

| Split | Samples | Attack % |
|---|---:|---:|
| Train | 2,345,597 | 96.43% |
| Validation | 502,628 | 96.43% |
| Test | 502,628 | 96.43% |

Leakage controls:

- Drop `src_ip`, `dst_ip`, `type`, `ts`.
- `type` la attack type/name, chi nen dung cho analysis hoac future multiclass work, khong dua vao binary training.
- IP fields co nguy co leakage cao vi co the gan chat voi label.

Preprocessing:

- Final feature count: **104 features**.
- Feature order la invariant quan trong giua ML va ZK.
- Frozen artifacts:
  - `outputs/preprocess/feature_schema.json`
  - `outputs/preprocess/feature_names.json`
  - `outputs/processed/feature_order.json`
  - `stage3_zk/artifacts/feature_order.json`

Notebook lien quan:

- `notebooks/01_data_sanity_check.ipynb`
- `notebooks/02_train_val_test_split.ipynb`
- `notebooks/03_preprocessing_pipeline.ipynb`

## 5. Stage 1.9: Baseline Models and Evaluation

Models:

- **XGBoost**: model manh hon ve detection performance.
- **Logistic Regression**: duoc chon cho Stage 3 ZK vi inference tuyen tinh, de bieu dien bang arithmetic constraints.

Artifacts:

- `outputs/models/logreg_baseline.pkl`
- `outputs/models/xgboost_baseline.pkl`
- `outputs/reports/baseline_metrics.json`
- `reports/baseline_extended_metrics.md`

Important evaluation note:

Dataset bi imbalance rat nang, Attack la majority class. Do do accuracy va Attack PR-AUC co the qua lac quan. Thesis nen nhan manh:

- Balanced Accuracy
- MCC
- Normal Recall / Specificity
- FPR
- FN/FP cost-based thresholding
- Calibration
- Drift/robustness proxy

Key test metrics from `reports/baseline_extended_metrics.md`:

| Model | Threshold | Balanced Acc | MCC | Attack Recall | Normal Recall | FPR |
|---|---:|---:|---:|---:|---:|---:|
| XGBoost default | 0.500000 | 0.992132 | 0.986851 | 0.999631 | 0.984634 | 0.015366 |
| XGBoost tuned@MCC | 0.489287 | 0.992081 | 0.986907 | 0.999639 | 0.984523 | 0.015477 |
| XGBoost tuned@BAcc | 0.968393 | 0.996811 | 0.955497 | 0.996729 | 0.996894 | 0.003106 |
| Logistic Regression default | 0.500000 | 0.923103 | 0.535818 | 0.935017 | 0.911189 | 0.088811 |
| Logistic Regression tuned@MCC | 0.088104 | 0.853183 | 0.761031 | 0.994600 | 0.711766 | 0.288234 |
| Logistic Regression tuned@BAcc | 0.620204 | 0.929770 | 0.538253 | 0.933095 | 0.926444 | 0.073556 |

Interpretation:

- XGBoost la baseline detection tot nhat.
- Logistic Regression hy sinh mot phan performance de co ZK feasibility.
- Neu viet thesis, can noi ro day la trade-off giua model expressiveness va proof efficiency.

## 6. Thesis-Grade ML Evaluation Pack

Repo co script suite trong `tools/` de tao Markdown reports va figures:

- `tools/reproduce.py`
- `tools/baseline_metrics.py`
- `tools/eval_decision_engineering.py`
- `tools/eval_drift_chunks.py`
- `tools/eval_semantic_group_ablation.py`
- `tools/eval_cost_based_thresholds.py`
- `tools/eval_zk_scaling_benchmark.py`

Recommended command:

```powershell
python tools/reproduce.py all-eval --ratios "0.25,0.5,1,2,5,10,20,50,100"
```

Outputs:

- `reports/baseline_extended_metrics.md`
- `reports/decision_engineering_baselines.md`
- `reports/drift_chunks.md`
- `reports/semantic_group_ablation.md`
- `reports/cost_based_thresholds.md`
- figures under `reports/figures/`

Decision engineering summary:

- XGBoost co calibration rat tot:
  - raw ECE: `0.000271`
  - Platt ECE: `0.000174`
  - Isotonic ECE: `0.000135`
- Logistic Regression raw probability calibration kem hon:
  - raw ECE: `0.121681`
  - Platt ECE: `0.010188`
  - Isotonic ECE: `0.000292`

Drift proxy:

- Test set duoc reorder theo `test_idx`, chia 20 chunks.
- XGBoost on dinh hon Logistic Regression.
- XGBoost default FPR mean/max: `0.014920 / 0.082228`.
- Logistic Regression default FPR mean/max: `0.119252 / 0.347480`.

Cost-based thresholding:

- Sweep FN/FP ratios: `0.25, 0.5, 1, 2, 5, 10, 20, 50, 100`.
- XGBoost duy tri cost/sample thap hon Logistic Regression ro rang.
- Noi dung nay huu ich de viet phan operational IDS trade-off.

## 7. Stage 2: Explainability

Muc tieu:

- Tao per-sample top-k explanation.
- Do stability trong tung model.
- Do overlap giua Logistic Regression va XGBoost.
- Chung minh semantic grouping giup explanation on dinh va ZK-friendly hon.

Notebook:

- `notebooks/05_stage2_topk_explainability.ipynb`
- `notebooks/05b_stage2_semantic_grouping.ipynb`

Top-k method:

- `k = 5`
- Logistic Regression contribution: `abs(w_i * x_i)`
- XGBoost contribution: SHAP-like `pred_contribs=True`, lay absolute value
- Subset analyzed: 1100 samples

Raw top-5 results:

| Metric | Value |
|---|---:|
| LogReg stability | 0.5847 |
| XGBoost stability | 0.4075 |
| Mean LogReg-XGB overlap | 0.1558 |
| Overlap std | 0.0820 |

Semantic groups:

| Group ID | Group Name | Meaning |
|---:|---|---|
| 1 | Protocol | Protocol-level features such as TCP/UDP/ICMP |
| 2 | Application | Service, HTTP, SSL, DNS, weird flags |
| 3 | ConnectionState | Connection state one-hot features |
| 4 | Ports | Source and destination ports |
| 5 | TrafficVolume | Bytes, packets, duration and volume signals |

Semantic results:

| Metric | Value |
|---|---:|
| LogReg semantic stability | 0.7794 |
| XGBoost semantic stability | 0.7429 |
| Mean semantic overlap | 0.3012 |
| Semantic overlap std | 0.1468 |

Semantic group frequency patterns:

| Model | Dominant raw groups |
|---|---|
| Logistic Regression | Application, Protocol, ConnectionState |
| XGBoost | TrafficVolume, Ports, Protocol |

Group-size normalization note:

- Application group rat lon, nen raw frequency co the bi bias.
- `reports/semantic_group_ablation.md` so sanh raw frequency voi normalized frequency.
- Sau khi normalized:
  - Logistic Regression: Protocol, ConnectionState, Ports noi bat hon.
  - XGBoost: Ports, Protocol, TrafficVolume noi bat hon.

Thesis implication:

- Raw feature-level explanation giua models khac nhau nhieu.
- Semantic-level explanation on dinh hon va gan voi mental model cua SOC analyst.
- Stage 3 dung semantic groups de giam circuit complexity: ranking 5 groups thay vi sorting 104 features.

## 8. Stage 3: ZK-XIDS

Muc tieu:

Chung minh correct inference va top-3 explanation ma khong tiet lo private input features.

ZK stack:

- Circom
- Groth16
- snarkjs `0.7.5`
- BN254 field

Public/private design:

- Private witness:
  - quantized and shifted input features `x_shifted[104]`
  - Stage 3.3 private `other2_ids`
- Public:
  - model weights/bias or model-binding public signals
  - claimed `y_hat`
  - Stage 3.3 claimed `top3_ids`

Model:

- Logistic Regression with 104 features.
- Quantized fixed-point arithmetic:
  - `Sx = 2^16`
  - `Sw = 2^12`
  - `x_int[i] = round(x[i] * Sx)`
  - `w_int[i] = round(w[i] * Sw)`
  - `b_int = round(b * Sx * Sw)`
  - `score_int = sum(x_int[i] * w_int[i]) + b_int`
  - `y_hat = 1 if score_int >= 0 else 0`

Important technique:

- Circom/snarkjs field arithmetic khong xu ly signed integers truc tiep theo cach ML mong doi.
- Project dung **shifted-input encoding**:
  - `x_shifted[i] = x_int[i] + maxAbsX`
  - Circuit recover `x_int[i] = x_shifted[i] - maxAbsX`
  - Range checks thuc hien tren non-negative shifted values.

Bounds:

- `maxAbsX = 297,270,816`
- `maxAbsW = 122,130`
- `maxAbsScore = 22,988,183,559`
- Report ghi rang cac gia tri nay van nho hon nhieu so voi field size, nen co safety margin lon.

### 8.1 Circuit Stages

| Stage | Circuit | Purpose |
|---|---|---|
| 3.1 | `stage3_zk/circuits/inference_only/inference_only.circom` | Prove correct Logistic Regression inference |
| 3.2 | `stage3_zk/circuits/semantic_groups/semantic_groups.circom` | Add private semantic group contribution aggregation |
| 3.3 | `stage3_zk/circuits/top3_explanation/top3_explanation.circom` | Prove top-3 semantic groups dominate the other 2 groups |

Stage 3.3 constraints:

- Check group IDs are in `{1,2,3,4,5}`.
- Check all 5 IDs are distinct.
- Check permutation via sum and sum of squares.
- Select private group contribution by ID using one-hot pattern.
- Prove each top-3 group contribution is greater than or equal to each other group.
- Optionally enforce ordering among top-3 with non-strict comparisons.

Security tests:

- Wrong explanation should fail witness/proof generation.
- Malicious `other2_ids` should fail.
- Out-of-range or duplicate group IDs should fail.
- Public top-3 validation recomputes expected values.

### 8.2 Latest ZK Evidence

Use [`stage3_zk/reports/LATEST_REPRO_REPORT.md`](../stage3_zk/reports/LATEST_REPRO_REPORT.md) as authoritative source for current ZK measurements.

Latest full run:

- Started: `2026-02-12T19:02:43+00:00`
- Finished: `2026-02-12T19:04:20+00:00`
- Duration: `97,000 ms`
- Command args included:
  - `stage = all`
  - `samples = [1, 2, 3]`
  - `build = True`
  - `clean = True`
  - `prove = True`
  - `verify = True`
  - `validate_proofs = True`

Complexity and communication:

| Stage | Constraints | Wires | Public Inputs | Private Inputs | R1CS bytes | WASM bytes | ZKey bytes | Proof bytes | Public bytes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 31 | 3,831 | 3,829 | 106 | 104 | 597,816 | 56,283 | 1,938,424 | 805 | 3,509 |
| 32 | 17,684 | 17,150 | 111 | 104 | 2,770,124 | 124,524 | 9,683,997 | 805 | 1,228 |
| 33 | 18,719 | 18,043 | 109 | 106 | 2,927,208 | 137,026 | 10,088,775 | 803 | 1,178 |

Selected run times:

| Step | Typical duration in latest report |
|---|---:|
| Build Stage 3.1 | 28,281 ms |
| Build Stage 3.2 | 22,875 ms |
| Build Stage 3.3 | 23,468 ms |
| Prove Stage 3.1 sample | about 953-1,030 ms |
| Verify Stage 3.1 sample | about 641-733 ms |
| Prove Stage 3.2 sample | about 1,328-1,546 ms |
| Verify Stage 3.2 sample | about 514-531 ms |
| Prove Stage 3.3 sample | about 1,266-1,468 ms |
| Verify Stage 3.3 sample | about 531-608 ms |

Stage 3.3 repeated benchmark:

- Report: `stage3_zk/reports/zk_scaling_benchmark.md`
- Stage: `33`
- Sample: `1`
- Runs total: `30`
- Warmup excluded: `2`
- Runs analyzed: `28`

| Step | mean ms | p50 ms | p95 ms |
|---|---:|---:|---:|
| prepare_input | 77 | 70 | 109 |
| witness_smoke | 87 | 78 | 150 |
| prove | 1,532 | 1,484 | 1,847 |
| verify | 588 | 562 | 696 |
| wall_total | 4,813 | 4,724 | 5,532 |

Important interpretation:

- Latest report measures CLI/harness wall-clock times, including process/spawn overhead.
- Older reports mention faster Node API timings. For thesis tables, use one measurement protocol consistently and state what is included.

## 9. Reproducibility Guide

Basic artifact consistency check:

```powershell
python tools/reproduce.py check
```

Full ML evaluation pack:

```powershell
python tools/reproduce.py all-eval --ratios "0.25,0.5,1,2,5,10,20,50,100"
```

ZK quick tests:

```powershell
python tools/reproduce.py zk --stage all --samples 1,2,3 --no-witness-smoke
```

ZK full evidence run:

```powershell
cd stage3_zk
npm run evidence:zk:full
```

ZK Stage 3.3 validation only:

```powershell
cd stage3_zk
npm run test:stage33:validate
```

ZK scaling benchmark:

```powershell
python tools/reproduce.py zk-scale --stage 33 --sample 1 --runs 30 --warmup 2
```

Environment warning:

- Reports say the canonical ML environment is Conda Python `3.10`.
- Some latest ZK evidence was generated with Python `3.12.3`.
- `requirements.in` lists ML dependencies, but `requirements.lock.txt` currently does not include the full ML stack. See "Known Issues" below.

## 10. Current Strengths

1. **Clear 3-stage thesis story**
   - Dataset and ML baseline.
   - Explainability and semantic abstraction.
   - ZK proof for privacy and explanation authenticity.

2. **Good thesis-grade evaluation**
   - Goes beyond accuracy.
   - Includes class imbalance metrics, threshold tuning, calibration, drift proxy, and cost-based thresholding.

3. **Strong ZK artifact trail**
   - Circuits implemented for 104 features.
   - Public/private signal design documented.
   - Security tests included.
   - Reproducibility evidence report exists.

4. **Explainability is tied to ZK feasibility**
   - Semantic grouping is not only interpretability, but also circuit complexity reduction.

5. **Defense-ready narrative**
   - The project has reports, figures, scripts, and reproducibility commands suitable for thesis defense.

## 11. Known Issues and Risks

These are useful for a third party reviewing or extending the project.

### 11.1 Dependency lock mismatch

`requirements.in` contains:

- `numpy`
- `pandas`
- `scikit-learn`
- `xgboost`
- `joblib`
- `matplotlib`

But `requirements.lock.txt` currently contains document/PDF-related packages only:

- `charset-normalizer`
- `lxml`
- `pillow`
- `pypdf`
- `python-docx`
- `reportlab`
- `typing_extensions`

Risk:

- `pip install -r requirements.lock.txt` may not reproduce the ML pipeline.

Suggested fix:

- Regenerate a real ML lock file from the canonical environment.
- Or split into:
  - `requirements-ml.lock.txt`
  - `requirements-docs.lock.txt`
  - `requirements-zk-node` handled by `package-lock.json`

### 11.2 ZK README should stay in sync

`stage3_zk/README.md` now exists and acts as the short onboarding page for Stage 3.

Suggested maintenance:

- Keep it synced with `stage3_zk/reports/LATEST_REPRO_REPORT.md` whenever ZK benchmarks or circuit stats are regenerated.

### 11.3 Conflicting benchmark numbers across reports

Historical Stage 3 benchmark artifacts include faster Node API timings, while latest report uses CLI/harness wall-clock timings around 1.3-1.5s prove and 0.5-0.7s verify.

Suggested thesis approach:

- Declare `LATEST_REPRO_REPORT.md` and `zk_scaling_benchmark.md` as current authoritative results.
- Move old numbers to "historical optimization notes" or remove them from final thesis tables.
- Always label whether timing includes witness generation, CLI overhead, build, or verification only.

### 11.4 Binary classification only

The project currently predicts `Normal` vs `Attack`.

Risk:

- TON_IoT includes attack types. Reviewers may ask why not multiclass.

Suggested response:

- Binary IDS is first scope.
- `type` was excluded from training to avoid leakage.
- Multiclass attack-type detection is a future-work extension.

### 11.5 Dataset split may not model temporal deployment

Current split is stratified random split over sampled data.

Risk:

- IDS deployment often faces temporal drift or file/source drift.

Suggested improvement:

- Add file-wise or time-wise split if timestamp/file metadata can be recovered.
- Compare random stratified split vs chronological/file holdout.

### 11.6 Logistic Regression performance gap

XGBoost is much stronger than Logistic Regression, but ZK uses Logistic Regression.

Risk:

- A reviewer may question practical IDS performance of the ZK model.

Suggested thesis framing:

- XGBoost is upper-performance baseline.
- Logistic Regression is the ZK-compatible privacy-preserving baseline.
- The research contribution is verifiable private inference plus explanation authenticity, not best possible plaintext IDS accuracy.

### 11.7 Trusted setup caveat

Groth16 requires circuit-specific trusted setup.

Suggested thesis wording:

- Current setup is proof-of-concept.
- Production deployment should use MPC ceremony for zkey contribution.
- Future work can compare universal-setup systems such as PLONKish/Halo2-style stacks.

### 11.8 Public model exposure

Weights are public in current design.

Risk:

- If model IP must be protected, current design does not hide the model.

Possible scope:

- Public model binding via model hash/commitment instead of exposing all weights.
- Private model proof design, if hiding weights becomes a requirement.

### 11.9 Privacy leakage through outputs

Verifier learns:

- `y_hat`
- top-3 semantic group IDs

Risk:

- Even if raw features are private, output explanation may leak some high-level behavioral information.

Suggested addition:

- Discuss output leakage explicitly in threat model and privacy analysis.

## 12. Suggested Scope Improvements for Thesis

This section is designed for a third party to propose or implement improvements.

### 12.1 Thesis writing improvements

1. Define explicit research questions:
   - RQ1: Can IDS inference be verified without revealing traffic features?
   - RQ2: Can semantic explanations be verified cryptographically?
   - RQ3: What is the cost of verifiable explanation compared with inference-only ZK?
   - RQ4: How much performance is lost when choosing ZK-friendly Logistic Regression over XGBoost?

2. Make the threat model precise:
   - Honest-but-curious verifier.
   - Potentially malicious prover.
   - Public model vs private input.
   - What is leaked by public outputs.

3. Separate three evaluation axes:
   - IDS detection performance.
   - Explanation stability and usefulness.
   - ZK proof cost and security tests.

4. Add a "source of truth" table:
   - Which report/file supplies final dataset numbers.
   - Which report/file supplies final ML metrics.
   - Which report/file supplies final ZK metrics.

5. Add limitations honestly:
   - Binary only.
   - Logistic Regression only for ZK.
   - Random split.
   - Groth16 trusted setup.
   - Proof generation not real-time for very high throughput without parallelization.

### 12.2 ML and data improvements

1. Add file-wise or time-wise validation:
   - Hold out one or more processed CSV shards.
   - Compare with current random stratified split.

2. Add attack-type analysis without using `type` for training:
   - Evaluate false negatives by attack type.
   - Report whether some attack families are missed more often.

3. Add confusion matrix per operating point:
   - Already present in decision engineering report.
   - Convert the most relevant ones into thesis-ready tables.

4. Improve imbalance discussion:
   - Explain why Normal is minority.
   - Explain why FPR matters for false alarms.
   - Explain why Attack recall matters for missed attacks.

5. Compare Logistic Regression quantized vs float:
   - Measure prediction agreement after quantization.
   - Report mismatch rate and examples.

6. Add calibration-aware threshold selection:
   - Compare raw, Platt, and isotonic thresholds.
   - Explain whether calibrated probabilities are used operationally.

### 12.3 Explainability improvements

1. Clarify semantic group construction:
   - List exact group sizes.
   - Explain why each feature belongs to each group.

2. Add group-size normalized analysis to main thesis:
   - Raw frequency favors large groups.
   - Normalized frequency gives a fairer view.

3. Add case studies:
   - One true positive.
   - One true negative.
   - One false negative.
   - For each, show prediction, top groups, and explanation narrative.

4. Add stability under perturbation:
   - Slightly perturb input values.
   - Check if top semantic groups remain stable.

5. Explain why top-3 groups are enough:
   - SOC triage use case.
   - Top-3 over 5 groups balances information and privacy.

### 12.4 ZK improvements

1. Keep `stage3_zk/README.md` updated:
   - Setup.
   - How to build circuits.
   - How to run evidence report.
   - How to interpret public signals.

2. Add model commitment:
   - Instead of exposing all public weights in every proof, publish model hash/commitment.
   - Discuss trade-off between verifier simplicity and communication size.

3. Clarify public signal encoding:
   - Negative weights appear as field elements.
   - Explain how verifier maps them back or checks expected public vector.

4. Benchmark with consistent modes:
   - CLI/harness timings.
   - Node API cryptographic timings.
   - Witness generation only.
   - Prove only.
   - Verify only.

5. Add proof batching or aggregation discussion:
   - Recursive SNARKs.
   - Batch verification.
   - Multi-sample proof.

6. Production trusted setup:
   - Document MPC ceremony requirement.
   - Include a short appendix on Groth16 assumptions.

7. Circuit optimization study:
   - Remove or keep defensive checks.
   - Show constraints vs security rationale.
   - Report effect on prove time.

8. Compare proof systems:
   - Groth16 vs PLONK/Halo2/noir/gnark at a conceptual level.
   - Explain why Groth16 was chosen for proof-of-concept.

### 12.5 Deployment and SOC scope

1. Add deployment architecture:
   - Prover at client side.
   - Verifier at SOC side.
   - Public model registry.
   - Proof and public signal transport.

2. Add throughput estimates:
   - Single prover.
   - Multi-worker prover pool.
   - Verifier throughput.

3. Add operational policy:
   - What happens if proof verification fails?
   - What happens if `y_hat = Attack`?
   - What if top-3 explanation conflicts with analyst intuition?

4. Add privacy policy:
   - What is hidden.
   - What is revealed.
   - What metadata still leaks.

## 13. Suggested Thesis Chapter Outline

1. **Introduction**
   - Motivation: privacy-preserving SOC monitoring.
   - Problem statement.
   - Contributions.

2. **Background**
   - IDS and TON_IoT.
   - Explainable AI for security.
   - Zero-knowledge proofs and Groth16.

3. **Dataset and Experimental Protocol**
   - Dataset loading and sampling.
   - Leakage controls.
   - Split strategy.
   - Preprocessing and 104-feature schema.

4. **Baseline Intrusion Detection Models**
   - Logistic Regression and XGBoost.
   - Imbalance-aware metrics.
   - Thresholding, calibration, and drift proxy.

5. **Explainability Layer**
   - Feature-level top-k.
   - Model agreement and stability.
   - Semantic grouping.
   - Group-size normalization.

6. **ZK-XIDS Design**
   - Threat model.
   - Quantization.
   - Shifted-input encoding.
   - Public/private signals.
   - Stage 3.1, 3.2, 3.3 circuit design.

7. **Evaluation**
   - ML performance.
   - Explanation stability.
   - ZK constraints, proof sizes, timing.
   - Security tests.

8. **Discussion**
   - Trade-offs.
   - Limitations.
   - Deployment considerations.

9. **Conclusion and Future Work**
   - Summary of contributions.
   - Future extensions: multiclass, XGBoost-in-ZK, batching, universal setup.

## 14. Third-Party Onboarding Checklist

For a reviewer or collaborator, recommended order:

1. Read this file.
2. Read `reports/thesis_project_map.md`.
3. Read `reports/dataset_summary.md`.
4. Read `reports/baseline_extended_metrics.md`.
5. Read `reports/stage2_summary.md`.
6. Read `stage3_zk/reports/LATEST_REPRO_REPORT.md`.
7. Run:

```powershell
python tools/reproduce.py check
```

8. If ML environment is ready, run:

```powershell
python tools/reproduce.py all-eval --ratios "0.25,0.5,1,2,5,10,20,50,100"
```

9. If ZK toolchain is ready, run:

```powershell
cd stage3_zk
npm run evidence:zk:quick
```

10. Before thesis finalization, reconcile all benchmark numbers against latest regenerated reports.

## 15. Open Questions

These questions are worth resolving before final thesis submission:

1. Should the final thesis use CLI/harness timing or Node API timing for ZK results?
2. Should `stage3_zk/README.md` include more low-level troubleshooting for Circom/snarkjs setup?
3. Should `requirements.lock.txt` be regenerated to include ML dependencies?
4. Can the split be strengthened with time/file holdout?
5. Should quantization mismatch between float LR and integer LR be measured explicitly?
6. Should the model be public, or should future work include model privacy?
7. Are top-3 semantic group IDs enough, or should exact group contribution ranges be optionally disclosed?
8. Should attack-type analysis be added as post-hoc evaluation?
9. Should old benchmark numbers be removed or marked historical?
10. Should public signals be compressed by model hash to reduce proof payload?

## 16. Glossary

| Term | Meaning |
|---|---|
| IDS | Intrusion Detection System |
| SOC | Security Operations Center |
| ZK | Zero-Knowledge |
| ZK-SNARK | Succinct non-interactive proof system with zero-knowledge property |
| Groth16 | Efficient ZK-SNARK proving system requiring trusted setup |
| Circom | DSL for writing arithmetic circuits |
| Witness | Private inputs and intermediate values satisfying a circuit |
| Public signals | Values visible to verifier |
| Top-k explanation | k most influential features/groups for a prediction |
| Semantic group | Human-readable feature category |
| MCC | Matthews Correlation Coefficient |
| FPR | False Positive Rate |
| Specificity | Normal recall, equal to true negative rate |
| Calibration | How well predicted probabilities match observed frequencies |

## 17. Final Takeaway

ZK-XIDS is not only an IDS model. It is a thesis prototype showing that **privacy-preserving, verifiable, explainable intrusion detection** is feasible:

- XGBoost demonstrates strong plaintext detection performance.
- Logistic Regression provides a ZK-compatible model path.
- Semantic grouping makes explanations more stable and circuit-friendly.
- Stage 3.3 proves top-3 explanation authenticity and rejects fake explanations.

The most valuable next work is to clean up reproducibility dependencies, standardize final benchmark numbers, strengthen the experimental split, and make the ZK threat model/deployment story sharper for thesis readers.
