# A Scoped Zero-Knowledge Framework for Verifiable Semantic Explanations under Private Inputs: An Intrusion Detection Case Study

This repository contains the full code, data, and documentation for a Master's thesis on **zero-knowledge verifiable semantic explanations under private inputs**. The implementation is organized as the ZK-XIDS intrusion detection case study.

This repository implements an intrusion detection case study of a scoped zero-knowledge proof pattern for verifiable semantic explanations under private inputs. The reusable part targets approved public linear/logistic tabular models with fixed semantic groups and a fixed reference vector, while the current empirical instantiation uses TON_IoT intrusion detection.

Scope guardrail: this is a public-model/private-input system. It does not claim model-agnostic verification, confidential-model proofs, or differential privacy. The main Stage 3.4 claim does not bind the private witness to a specific log row; an optional Stage 3.5 appendix prototype explores an input-commitment layer for that audit binding.

## Project Overview
- **Objective:** Develop and evaluate a scoped public-model/private-input proof pattern for verifiable semantic explanations, instantiated as a privacy-preserving IDS case study using zero-knowledge proofs (ZKP).
- **Dataset:** TON_IoT Network dataset (23 processed CSV files, 46 columns, ~22M rows)
- **Stages:**
  1. **Stage 1:** Data sanity check, stratified train/val/test split, leakage analysis
  2. **Stage 2:** Top-k explainability (LogReg, XGBoost, semantic grouping, stability analysis)
  3. **Stage 3:** ZK-XIDS implementation (Circom 2.x, Groth16, four main circuit stages; Stage 3.4 circuit pragma is 2.1.9 and was rebuilt with WSL Circom 2.2.3; Stage 3.5 is an optional input-commitment appendix prototype)

## Folder Structure
- `data/` - Raw and processed datasets
- `notebooks/` - Jupyter notebooks for data analysis, preprocessing, and model training
- `outputs/` - Model artifacts, splits, reports, and explainability results
- `reports/` - Markdown reports for each stage
- `stage3_zk/` - ZK-XIDS implementation, circuits, scripts, and final summary

## Key Features
- **Verifiable semantic explanation proof pattern** in a public-model/private-input setting
- **Privacy-preserving inference** using ZKP, with input-feature privacy and intentional output disclosure
- **Explainable AI**: Top-k feature attribution, semantic grouping
- **Academic explainability extension**: semantic-group Exact SHAP over the 5 semantic groups, with Stage 3.4 SNARK verification for the public Logistic Regression model
- **Reproducible splits** and pipeline
- **Imbalance-aware, thesis-grade evaluation** (operating points, calibration, drift proxy, cost-based thresholds)
- **Comprehensive documentation** for thesis defense

## Thesis Contribution Framing

- C1. A public-model/private-input proof pattern for verifiable semantic explanations over public linear/logistic tabular models, instantiated on intrusion detection.
- C2. A semantic-group explanation abstraction that maps high-dimensional tabular features into human-readable groups.
- C3. A SNARK-verifiable semantic-group Exact SHAP top-3 method for public Logistic Regression with fixed reference masking.
- C4. A reproducible case-study evaluation covering IDS performance, explanation stability, proxy-vs-ExactSHAP comparison, proof cost, output leakage, reference sensitivity, model-version binding, and negative tests.

## Documentation (start here)

- **Thesis-oriented project map (recommended):** `reports/thesis_project_map.md`
- Stage 1 dataset + protocol summary: `reports/dataset_summary.md`
- Stage 2 explainability summary: `reports/stage2_summary.md`
- Formal framework and guarantees: `reports/formal_framework_and_security_guarantees.md`
- Semantic-group Exact SHAP extension: `reports/exact_shap_semantic_groups.md`, `reports/method_choice_exact_shap.md`, and `reports/stage34_thesis_integration.md`
- Model visibility / hidden-model future work: `reports/model_visibility_threat_model.md`
- Model registry / verifier policy: `reports/model_registry_and_verifier_policy.md`
- Optional input-commitment appendix prototype: `reports/input_commitment_appendix.md` and `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md`
- Output leakage and reference sensitivity: `reports/stage34_output_leakage_audit.md`, `reports/exact_shap_reference_sensitivity.md`
- Thesis figure package: `reports/thesis_figures.md` and `reports/figures/thesis/`
- Stage 3 ZK system summary: `stage3_zk/reports/FINAL_SUMMARY.md`
- Full report index (all markdown + where figures live): `reports/README.md`

## Quickstart (no notebooks required if artifacts already exist)

1) Install Python 3.10+ (Conda recommended).
2) Install dependencies:
  - For thesis-grade ML reproduction, use the canonical Conda Python 3.10 environment (`py310` in the examples below).
  - `requirements.in` lists the direct ML dependencies used by the pipeline.
  - `requirements-ml.lock.txt` pins the direct ML/evaluation dependencies used by the thesis reports where available.
  - `requirements-docs.lock.txt` pins document/report helper dependencies.
  - `requirements.lock.txt` is a meta lock that installs both stacks; ZK Node dependencies are handled separately by `stage3_zk/package-lock.json`.
3) Run a consistency check (feature order + required artifacts):
  - `python tools/reproduce.py check`
4) Generate the full thesis-grade ML evaluation pack (reports + figures):
  - `python tools/reproduce.py all-eval --ratios "0.25,0.5,1,2,5,10,20,50,100"`
  - PowerShell note: the `--ratios` value must be quoted exactly like above.

If you want strict, warning-free reproducibility for pickled baseline models, run under the canonical Conda env (example name: `py310`):
- `conda run -n py310 python tools/reproduce.py all-eval --ratios "0.25,0.5,1,2,5,10,20,50,100"`

## Full pipeline (regenerate everything from data)

If you need to regenerate the ML pipeline outputs from scratch, run notebooks in order:
- `notebooks/01_data_sanity_check.ipynb`
- `notebooks/02_train_val_test_split.ipynb`
- `notebooks/03_preprocessing_pipeline.ipynb`
- `notebooks/04_train_and_evaluate_baseline.ipynb`
- `notebooks/05_stage2_topk_explainability.ipynb`
- `notebooks/05b_stage2_semantic_grouping.ipynb`
- `notebooks/06_stage3_prepare_artifacts.ipynb`

For ZK-XIDS execution, see `stage3_zk/README.md` and `stage3_zk/reports/FINAL_SUMMARY.md`.

### Reproducibility helpers

- One-command evaluation pack (generates all ML evaluation reports + figures):
  - `python tools/reproduce.py all-eval --ratios "0.25,0.5,1,2,5,10,20,50,100"`
  - (Optional) include ZK scaling benchmark: add `--include-zk-scale`

- Artifact consistency checks (104 features, identical feature order across ML-to-ZK):
  - `python tools/reproduce.py check`
- Final numbers source-of-truth table:
  - `python tools/reproduce.py source-truth`
  - Thesis-friendly artifact: `reports/final_numbers_source_of_truth.md`
- Baseline evaluation with imbalance-aware metrics (adds specificity/FPR, MCC, threshold tuning on validation):
  - `python tools/reproduce.py metrics`
  - Thesis-friendly summary: `reports/baseline_extended_metrics.md`
- Decision-engineering evaluation (tradeoff curves + calibration + operating points):
  - `python tools/reproduce.py eval`
  - Thesis-friendly artifact: `reports/decision_engineering_baselines.md` + figures under `reports/figures/`
- Drift/robustness check (metric stability across ordered test chunks):
  - `python tools/reproduce.py drift --chunks 20`
  - Thesis-friendly artifact: `reports/drift_chunks.md` + figures under `reports/figures/`
- File-wise holdout robustness check (train on earlier-numbered files, test on held-out later files):
  - `python tools/reproduce.py file-holdout`
  - Thesis-friendly artifact: `reports/filewise_holdout.md`
- Attack-type post-hoc error analysis (`type` used only after prediction, not for training):
  - `python tools/reproduce.py attack-types`
  - Thesis-friendly artifact: `reports/attack_type_error_analysis.md`
- Semantic-group ablation (raw group frequency vs size-normalized frequency):
  - `python tools/reproduce.py semantic-groups`
  - Thesis-friendly artifact: `reports/semantic_group_ablation.md` + figures under `reports/figures/`
- Float-vs-quantized Logistic Regression agreement (ML-to-ZK validity check):
  - `python tools/reproduce.py quant-agreement --splits val,test`
  - Thesis-friendly artifact: `reports/float_vs_quantized_lr_agreement.md`
- Exact SHAP ranking margin / stability self-assessment:
  - `python tools/reproduce.py ranking-margin --splits val,test`
  - Thesis-friendly artifact: `reports/exact_shap_ranking_margin.md`
- Semantic-group Exact SHAP + Stage 3.4 verification:
  - `python tools/eval_exact_shap_semantic_groups.py`
  - `python tools/reproduce.py stage34-vectors`
  - `python tools/reproduce.py zk-stage34 --samples 1,2,3,4,5,6,7,8`
  - Supplemental batch smoke test: `python tools/reproduce.py stage34-batch-smoke --samples 30 --prove 30 --seed 34030`
  - Optional policy/evidence helpers: `python tools/generate_model_registry.py`, `python tools/verify_stage34_policy.py --self-test`, `python tools/benchmark_stage34.py --sample 1 --runs 30 --warmup 2`
  - Thesis-friendly artifacts: `outputs/explainability/exact_shap_semantic_groups.csv`, `reports/formal_framework_and_security_guarantees.md`, `reports/exact_shap_semantic_groups.md`, `reports/method_choice_exact_shap.md`, `reports/stage34_thesis_integration.md`, `reports/stage34_case_studies.md`, `reports/stage34_output_leakage_audit.md`, `reports/exact_shap_reference_sensitivity.md`, `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md`, `stage3_zk/reports/STAGE34_PROOF_REPORT.md`, `stage3_zk/reports/STAGE34_BATCH_SMOKE_REPORT.md`
- Optional Stage 3.5 input-commitment appendix prototype:
  - From `stage3_zk/`: `npm run compile:stage35` if build artifacts are missing, then `npm run evidence:stage35`
  - Thesis-friendly artifacts: `reports/input_commitment_appendix.md`, `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md`
- ZK scaling benchmark (prove/verify timing p50/p95 across many runs):
  - `python tools/reproduce.py zk-scale --stage 33 --sample 1 --runs 30 --warmup 2`
  - Thesis-friendly artifact: `stage3_zk/reports/zk_scaling_benchmark.md`
- Cost-based threshold selection (explicit FN/FP cost ratios):
  - `python tools/reproduce.py cost --ratios "0.25,0.5,1,2,5,10,20,50,100"`
  - Thesis-friendly artifact: `reports/cost_based_thresholds.md`

### Thesis artifact index (quick links)

Core ML evaluation:
- `reports/final_numbers_source_of_truth.md`
- `reports/baseline_extended_metrics.md`
- `reports/decision_engineering_baselines.md` (plus `reports/figures/decision_engineering_*`)
- `reports/drift_chunks.md` (plus `reports/figures/drift_chunks_*`)
- `reports/semantic_group_ablation.md` (plus `reports/figures/semantic_group_ablation_*`)
- `reports/float_vs_quantized_lr_agreement.md`
- `reports/exact_shap_ranking_margin.md`
- `reports/cost_based_thresholds.md` (plus `reports/figures/cost_thresholds_*`)

ZK evaluation:
- `stage3_zk/reports/FINAL_SUMMARY.md`
- `stage3_zk/reports/zk_scaling_benchmark.md`
- `stage3_zk/reports/STAGE34_PROOF_REPORT.md`
- `stage3_zk/reports/STAGE34_BATCH_SMOKE_REPORT.md`
- `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md` (appendix-only)
- `stage3_zk/reports/zk_stage34_scaling_benchmark.md`

For a single page listing of *all* markdown artifacts and where to find figures, see: `reports/README.md`.

#### Note on environments (important)

The baseline models under `outputs/models/*.pkl` were originally trained from the notebooks in a **Conda Python 3.10** environment.
If you run `metrics` under a different Python / scikit-learn / xgboost version, you may see warnings when loading the pickles.

For strict, warning-free reproducibility, regenerate baselines and metrics inside the same Conda env (example env name: `py310`):
- Retrain + overwrite baseline model artifacts:
  - `conda run -n py310 python tools/train_baselines.py`
- Recompute imbalance-aware baseline metrics:
  - `conda run -n py310 python tools/reproduce.py metrics`
- Generate operating-point curves + calibration figures:
  - `conda run -n py310 python tools/reproduce.py eval`
- Generate drift/robustness chunk plots:
  - `conda run -n py310 python tools/reproduce.py drift --chunks 20`
- Generate semantic-group ablation report + plots:
  - `conda run -n py310 python tools/reproduce.py semantic-groups`
- Generate ZK scaling benchmark report (may take a few minutes for 30+ runs):
  - `conda run -n py310 python tools/reproduce.py zk-scale --stage 33 --sample 1 --runs 30 --warmup 2`
- Generate cost-based threshold report + plots:
  - `conda run -n py310 python tools/reproduce.py cost --ratios "0.25,0.5,1,2,5,10,20,50,100"`
- One-command evaluation pack (recommended for defense):
  - `conda run -n py310 python tools/reproduce.py all-eval --ratios "0.25,0.5,1,2,5,10,20,50,100"`
  - include ZK scaling benchmark: add `--include-zk-scale`

If you prefer not to use Conda, you can also re-run `notebooks/04_train_and_evaluate_baseline.ipynb` under your chosen pinned environment.
- ZK test harness (prepare inputs + witness smoke + Stage 3.3 security tests):
  - `python tools/reproduce.py zk --stage all --samples 1,2,3`
  - or from `stage3_zk/`: `npm run test:zk`
  - quick mode (no WASM/witness required): `python tools/reproduce.py zk --stage all --no-witness-smoke` or `npm run test:zk:quick`
  - clean mode (removes stale generated inputs/witness/proofs): `python tools/reproduce.py zk --stage all --clean` or `npm run test:zk:clean`
  - full end-to-end (build + witness + prove + verify): `npm run test:zk:full`
  - evidence report (writes JSON+MD under `stage3_zk/reports/`): `cd stage3_zk; npm run evidence:zk:quick` or `npm run evidence:zk:full`
    - The stable, thesis-friendly artifact is: `stage3_zk/reports/LATEST_REPRO_REPORT.md` (includes a "Complexity & Communication" table with constraint counts and artifact sizes)
  - validate existing Stage 3.3 proof public signals (opt-in): `npm run test:stage33:validate` (or `python tools/reproduce.py zk --stage 33 --validate-proofs`)

## References
- TON_IoT Dataset: https://research.unsw.edu.au/projects/toniot-datasets
- Circom: https://docs.circom.io/
- Groth16: https://eprint.iacr.org/2016/260
