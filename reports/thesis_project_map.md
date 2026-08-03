# Thesis-Oriented Project Map - ZK-XIDS (TON_IoT)

This document maps the repo into a thesis-friendly structure: **what each stage does**, **which notebooks/scripts implement it**, and **which artifacts are produced/consumed**.

## 0) One-paragraph system description (thesis-ready)
This repository implements an intrusion detection case study of a scoped zero-knowledge proof pattern for verifiable semantic explanations under private inputs. The empirical instantiation uses the TON_IoT Network dataset, an approved public Logistic Regression IDS model, fixed semantic groups, and Circom/Groth16 proofs. Stage 3.4 verifies that the public prediction and a valid ordered non-increasing top-3 semantic-group Exact SHAP explanation are computed from the same private feature vector.

Scope guardrail: the implemented main claim is public-model/private-input verification for public linear/logistic tabular models with fixed semantic groups and a fixed reference vector. It is not model-agnostic, does not hide model weights, and does not provide differential privacy. Stage 3.4 does not bind the witness to a specific log row by itself; Stage 3.5 is an optional appendix prototype for an input-commitment binding point.

---

## 1) Repository layout (how to read it)

- `data/`
  - `raw/`: original/raw CSV (e.g., train/test network file).
  - `processed/Processed_Network_dataset/`: 23 processed CSV shards used for scalable loading.
- `notebooks/`: the end-to-end ML pipeline (01 -> 06).
- `outputs/`: **all ML artifacts** produced by notebooks (splits, preprocessing, arrays, models, explainability metrics).
- `reports/`: thesis-friendly markdown summaries for Stage 1-3.
- `stage3_zk/`: ZK implementation for the scoped public-model/private-input prototype: circuits, scripts, ZK artifacts, test vectors, proofs, benchmarks, and an optional Stage 3.5 input-commitment appendix prototype.

---

## 2) Global invariants (important for reproducibility section)

- Dataset mode used throughout ML pipeline: `processed_stratified_sample_23files_frac0.15`
  - recorded in `outputs/splits/data_manifest.json`
- Random seed: `42` (used for sampling/splits and Stage 2 stability sampling)
  - recorded in `outputs/splits/split_meta.json`
- Final feature count: **104**
  - recorded in `outputs/preprocess/feature_schema.json`
  - feature names/order frozen in `outputs/preprocess/feature_names.json` and `outputs/processed/feature_order.json`

> Note on docs: Stage 3 implementation and artifacts in `stage3_zk/` use **104 features**; references to the 87 -> 104 upgrade in older `stage3_zk/reports/` are historical context.

---

## 3) Stage-by-stage mapping (notebooks -> artifacts -> thesis sections)

### Stage 1 - Data sanity, leakage controls, and stratified split

**Thesis sections**: Dataset description, experimental protocol, leakage analysis, split strategy.

**Notebook(s)**
- `notebooks/01_data_sanity_check.ipynb`
- `notebooks/02_train_val_test_split.ipynb`

**Outputs produced**
- Split indices + metadata:
  - `outputs/splits/train_idx.npy`, `val_idx.npy`, `test_idx.npy`
  - `outputs/splits/split_meta.json`
- Dataset manifest (what files + fraction + mode):
  - `outputs/splits/data_manifest.json`
- Narrative summary (already thesis-friendly):
  - `reports/dataset_summary.md`

**Key thesis points**
- Class imbalance is extreme (Attack much greater than Normal), so evaluation should emphasize PR-AUC / recall / FNR.
- Leakage-prone identifiers are excluded from training (`src_ip`, `dst_ip`, `type`; and `ts` flagged in report).

---

### Stage 1.5 - Preprocessing pipeline and feature freezing (104 features)

**Thesis sections**: Feature engineering, preprocessing, encoding, final feature space definition.

**Notebook(s)**
- `notebooks/03_preprocessing_pipeline.ipynb`

**Outputs produced**
- Preprocessing pipeline + schema:
  - `outputs/preprocess/preprocess.pkl`
  - `outputs/preprocess/feature_schema.json`
  - `outputs/preprocess/feature_names.json`
- Processed arrays (model-ready):
  - `outputs/processed/X_train.npy`, `X_val.npy`, `X_test.npy`
  - `outputs/processed/y_train.npy`, `y_val.npy`, `y_test.npy`
  - `outputs/processed/feature_order.json`

**Key thesis points**
- Feature schema (numeric/categorical/boolean) is frozen; downstream explainability and ZK circuits depend on **exact feature order**.

---

### Stage 1.9 - Baseline model training and evaluation

**Thesis sections**: Baselines, evaluation metrics, justification for choosing LR for ZK.

**Notebook(s)**
- `notebooks/04_train_and_evaluate_baseline.ipynb`

**Outputs produced**
- Models:
  - `outputs/models/logreg_baseline.pkl`
  - `outputs/models/xgboost_baseline.pkl`
- Metrics (used in Stage 2 report and thesis tables):
  - `outputs/reports/baseline_metrics.json`

**Key thesis points**
- XGBoost provides strong performance; Logistic Regression is selected for Stage 3 because its inference is ZK-friendly (linear constraints).

---

## 3.9) Thesis-grade evaluation pack (scripted, reproducible)

This repo includes a script-first evaluation suite that is designed to be defense-ready (Markdown reports + figures) and robust under extreme class imbalance.

**Single entrypoint**
- `python tools/reproduce.py all-eval --ratios "0.25,0.5,1,2,5,10,20,50,100"`
  - (Optional) include ZK scaling benchmark: add `--include-zk-scale`

**Artifacts produced**
- Imbalance-aware baseline metrics + threshold tuning:
  - `reports/baseline_extended_metrics.md`
- Decision engineering (tradeoff curves + calibration + operating points):
  - `reports/decision_engineering_baselines.md` + `reports/figures/decision_engineering_*`
- Drift/robustness proxy (metric stability across ordered test chunks):
  - `reports/drift_chunks.md` + `reports/figures/drift_chunks_*`
- File-wise holdout robustness check (train on earlier-numbered files, evaluate on held-out later files):
  - `reports/filewise_holdout.md` + `outputs/reports/filewise_holdout.json`
- Attack-type post-hoc error analysis (`type` used only after prediction):
  - `reports/attack_type_error_analysis.md` + `outputs/reports/attack_type_error_analysis.csv`
- Semantic-group ablation (raw vs size-normalized group frequency):
  - `reports/semantic_group_ablation.md` + `reports/figures/semantic_group_ablation_*`
- Float-vs-quantized Logistic Regression agreement:
  - `reports/float_vs_quantized_lr_agreement.md` + `outputs/reports/float_vs_quantized_lr_examples.csv`
- Exact SHAP ranking margin:
  - `reports/exact_shap_ranking_margin.md` + `outputs/reports/exact_shap_ranking_margin_examples.csv`
- Cost-based threshold selection (explicit FN/FP ratios):
  - `reports/cost_based_thresholds.md` + `reports/figures/cost_thresholds_*`
- ZK prove/verify scaling benchmark (p50/p95 across repeated runs):
  - `stage3_zk/reports/zk_scaling_benchmark.md`

---

### Stage 2 - Per-sample top-k explanations + stability/overlap; semantic grouping

**Thesis sections**: Explainability method, stability analysis, semantic abstraction for ZK efficiency.

**Notebook(s)**
- `notebooks/05_stage2_topk_explainability.ipynb`
- `notebooks/05b_stage2_semantic_grouping.ipynb`

**Outputs produced (all under `outputs/stage2/`)**
- Per-sample top-k indices:
  - `topk_logreg.npy`, `topk_xgb.npy`
- Raw-feature stability/overlap:
  - `stability_summary.json`, `overlap_summary.json`
- Semantic stability/overlap:
  - `semantic_stability_summary.json`, `semantic_overlap_summary.json`
- Frequency summaries:
  - `top10_frequency_logreg.csv`, `top10_frequency_xgb.csv`
  - `semantic_group_frequency_logreg.csv`, `semantic_group_frequency_xgb.csv`

**Narrative summary**
- `reports/stage2_summary.md`

**Key thesis points**
- Raw feature-level top-k differs significantly across models, but semantic-group views are more stable and align better with a SOC analyst mental model.
- Stage 3 uses semantic groups to reduce circuit complexity (prove rankings over 5 groups instead of sorting many one-hot features).

---

### Stage 3 (prep) - Export ML artifacts into ZK-ready form

**Thesis sections**: Bridging ML to ZK, model publication, quantization/bounds, semantic mapping.

**Notebook(s)**
- `notebooks/06_stage3_prepare_artifacts.ipynb`

**Outputs produced**
- Written into `stage3_zk/artifacts/`:
  - `feature_order.json` (frozen ordering for circuits)
  - `group_map.json` (feature index to semantic group id)
  - `model_public.json` (quantized LR weights/bias)
  - `bounds.json` (maxAbsX/maxAbsW/maxAbsScore)

---

## 4) Stage 3 - ZK implementation map (circuits/scripts/tests)

**Thesis sections**: Threat model, ZK design, public/private signals, security tests, benchmarks.

### 4.1 ZK artifacts (published model + constraints)

- Model parameters and scaling (public model binding):
  - `stage3_zk/artifacts/model_public.json` (`n=104`, `Sx`, `Sw`, `w_int[]`, `b_int`)
- Bounds for range checks and soundness:
  - `stage3_zk/artifacts/bounds.json`
- Semantic grouping mapping:
  - `stage3_zk/artifacts/group_map.json` (5 groups; per-feature group id)

### 4.2 Circuits (Circom)

- Stage 3.1: `stage3_zk/circuits/inference_only/`
- Stage 3.2: `stage3_zk/circuits/semantic_groups/`
- Stage 3.3: `stage3_zk/circuits/top3_explanation/`
- Stage 3.4: `stage3_zk/circuits/exact_shap_top3/`
- Stage 3.5 appendix: `stage3_zk/circuits/exact_shap_top3_commitment/`

**Core design choice (thesis highlight)**
- Use **shifted-input encoding** to represent signed integers robustly in field arithmetic:
  - witness uses `x_shifted[i] = x_int[i] + maxAbsX` (non-negative), enabling correct range checks.

### 4.3 Scripts (build/prove/verify/benchmark)

Scripts are grouped by stage:
- `stage3_zk/scripts/stage 3.1/`
  - `02_build_circuit.ps1`, `03_generate_proof.sh`, `04_verify_proof.sh`, `05_benchmark.py` (optional)
  - input prep: `01_prepare_input.py` converts `test_vectors/test_sample_k.json` to `circuits/.../build/input_sample_k.json`
- `stage3_zk/scripts/stage 3.2/`, `stage3_zk/scripts/stage 3.3/`, `stage3_zk/scripts/stage 3.4/`, and `stage3_zk/scripts/stage 3.5/` are analogous stage-specific helpers.

Recommended single entrypoint (Windows-friendly):
- `stage3_zk/scripts/run_stage3_tests.py` (invoked via npm scripts)
- Thesis evidence artifact: `stage3_zk/reports/LATEST_REPRO_REPORT.md`

### 4.4 Validation and security tests (Stage 3.3/3.4)

- Functional validation:
  - `stage3_zk/scripts/stage 3.3/validate_stage33.py` recomputes expected top-3 and compares with proof public signals.
- Adversarial tests (thesis security evaluation section):
  - `stage3_zk/scripts/stage 3.3/test_wrong_explanation.py` (wrong top-3 should fail witness generation)
  - `stage3_zk/scripts/stage 3.3/test_malicious_other2.py`
  - `stage3_zk/scripts/stage 3.4/test_stage34_negative.py`

### 4.5 Benchmarks (reported results)

For thesis tables/figures, use:
- `stage3_zk/reports/LATEST_REPRO_REPORT.md` (authoritative, reproducible timings + constraints + artifact sizes)
- `stage3_zk/reports/FINAL_SUMMARY.md` and `stage3_zk/reports/stage3.md` (narrative/technical background)
- `stage3_zk/reports/STAGE34_PROOF_REPORT.md` and `stage3_zk/reports/zk_stage34_scaling_benchmark.md` (Stage 3.4 Exact SHAP evidence)
- `reports/input_commitment_appendix.md` and `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md` (appendix-only input-commitment feasibility evidence)
- `reports/model_registry_and_verifier_policy.md`, `reports/stage34_output_leakage_audit.md`, and `reports/exact_shap_reference_sensitivity.md` (thesis-facing policy and self-assessment)

---

## 5) Artifact inventory (quick reference table)

| Purpose | Where | Main files |
|---|---|---|
| Split protocol | `outputs/splits/` | `*_idx.npy`, `split_meta.json`, `data_manifest.json` |
| Preprocessing | `outputs/preprocess/` | `preprocess.pkl`, `feature_schema.json`, `feature_names.json` |
| Model-ready arrays | `outputs/processed/` | `X_*.npy`, `y_*.npy`, `feature_order.json` |
| Baseline models | `outputs/models/` | `logreg_baseline.pkl`, `xgboost_baseline.pkl` |
| Metrics | `outputs/reports/` | `baseline_metrics.json` |
| Explainability outputs | `outputs/stage2/` | `topk_*.npy`, `*_summary.json`, `*_frequency*.csv` |
| ZK public artifacts | `stage3_zk/artifacts/` | `model_public.json`, `bounds.json`, `group_map.json`, `feature_order.json`, `model_registry_stage34.json` |
| ZK proofs | `stage3_zk/outputs/proofs/` | `proof_*.json`, `public_*.json` |

---

## 6) Suggested thesis chapter mapping (practical outline)

- Chapter 1: Motivation + problem statement (verifiable semantic explanations under private inputs)
- Chapter 2: Background
  - IDS + explainability + ZK-SNARKs
- Chapter 3: Dataset & experimental protocol
  - Stage 1: sampling, leakage controls, splits
- Chapter 4: ML baselines
  - Stage 1.9: LogReg vs XGB results and rationale
- Chapter 5: Explainability
  - Stage 2: top-k definitions, stability/overlap, semantic grouping
- Chapter 6: Verifiable semantic explanation framework and IDS instantiation
  - Stage 3.1/3.2/3.3/3.4 circuits, public/private signals, bounds, shifted encoding
- Chapter 7: Evaluation
  - Model metrics + explanation stability + ZK benchmarks + security tests
- Chapter 8: Limitations & future work

---

## 7) Minimum reproducible run checklist (for appendix)

1) Run notebooks 01 -> 06 to regenerate `outputs/` and ZK artifacts.
2) In `stage3_zk/`, run a full reproducibility+evidence run: `npm run evidence:zk:full`
3) Use `stage3_zk/reports/LATEST_REPRO_REPORT.md` for the appendix table (timings, constraints, proof/public sizes).
4) Use `python tools/reproduce.py zk-stage34 --samples 1,2,3,4,5,6,7,8` for Stage 3.4 Exact SHAP proof evidence.
5) Use `python tools/verify_stage34_policy.py --self-test` for verifier-side model-version binding evidence.
6) Optional appendix only: from `stage3_zk/`, use `npm run compile:stage35` if build artifacts are missing, then `npm run evidence:stage35` for input-commitment feasibility evidence.
