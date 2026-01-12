# ZK-XIDS: Zero-Knowledge Privacy-Preserving Intrusion Detection System

This repository contains the full code, data, and documentation for the Master's thesis project:  
**ZK-XIDS: Zero-Knowledge Privacy-Preserving Intrusion Detection System for Network Security**.

---

## TL;DR
- **Goal:** Privacy-preserving + auditable intrusion detection using **Zero-Knowledge Proofs (ZK)**, with **explainability** artifacts that can also be verified.
- **Dataset:** TON_IoT Network dataset (23 processed CSV files, 46 columns, ~22M rows).
- **Pipeline:**  
  **Stage 1** (sanity + splits + leakage) → **Stage 2** (top-k explainability + semantic grouping + stability) → **Stage 3** (Circom 2.1.9 + Groth16, 3 circuit stages).

---

## Key Results (What this repo proves you can reproduce)
### Stage 2 (Explainability artifacts)
You should be able to reproduce and/or regenerate these outputs:
- **Top-k frequency CSVs**
  - `top10_frequency_logreg.csv`, `top10_frequency_xgb.csv`
  - `semantic_group_frequency_logreg.csv`, `semantic_group_frequency_xgb.csv`
- **Stability / overlap summaries (JSON)**
  - `stability_summary.json`, `overlap_summary.json`
  - `semantic_stability_summary.json`, `semantic_overlap_summary.json`
  - `diversity_analysis.json`
- **Figures**
  - `fig_top10_logreg.png`, `fig_top10_xgb.png`
  - `fig_semantic_groups_logreg.png`, `fig_semantic_groups_xgb.png`
- **Numpy artifacts (optional)**
  - `topk_logreg.npy`, `topk_xgb.npy`

> These files are generated in your Stage 2 output folder (wherever your notebooks/scripts currently save them).

### Stage 3 (ZK proof artifacts + benchmark outputs)
You should be able to generate and verify proofs, and produce benchmark JSON files such as:
- Proof & public inputs (examples):
  - `proof_sample_1.json`, `public_sample_1.json`
  - `proof_stage32_sample_1.json`, `public_stage32_sample_1.json`
  - `proof_stage33_sample_1.json`, `public_stage33_sample_1.json`
- Benchmarks:
  - `benchmark_results.json`
  - `benchmark_optimized.json`
  - `benchmark_stage32.json`
  - `benchmark_stage33.json`

---

## Folder Structure
- `data/` — Raw and processed datasets (not tracked; see Dataset Setup)
- `notebooks/` — Jupyter notebooks for Stages 1–2
- `outputs/` — Splits, models, metrics, explainability artifacts
- `reports/` — Markdown reports for each stage
- `stage3_zk/` — ZK-XIDS implementation (Circom/Groth16), scripts, circuits, proofs, benchmarks

Inside `stage3_zk/`:
- `scripts/`
  - `stage 3.1/` (setup → prepare input → build circuit → prove → verify → benchmark)
  - `stage 3.2/` (stage-32 specific scripts)
  - `stage 3.3/` (stage-33 specific scripts)

---

## Requirements
### Python (Stages 1–2 + benchmarks)
- Python **3.10+**
- Recommended: Conda / venv
- Packages: defined in `requirements.txt` (if present)

### ZK (Stage 3)
- **Node.js** (LTS recommended)
- **Circom 2.1.9**
- **snarkjs**
- (Optional) PowerShell (if you use `.ps1` script on Windows)

---

## Environment Setup
### Option A — Conda (recommended)
```bash
conda create -n zkxids python=3.10 -y
conda activate zkxids
pip install -r requirements.txt
```

### Option B — venv
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Dataset Setup (TON_IoT)
Place processed CSV files here (example):
```
data/ton_iot/processed/
  ├── *.csv   (23 files)
```

Recommended `.gitignore`:
```
data/
outputs/
**/*.zkey
**/*.r1cs
**/*.wasm
```

---

## How to Reproduce (End-to-End)

### Stage 1 — Data sanity + splits + leakage analysis
Run notebooks in order:
1. `notebooks/01_data_sanity_check.ipynb`
2. `notebooks/02_train_val_test_split.ipynb`
3. `notebooks/03_preprocessing_pipeline.ipynb`

**Expected outputs (examples):**
- `outputs/splits/train.csv`, `outputs/splits/val.csv`, `outputs/splits/test.csv`
- Stage 1 report files under `reports/` or exported markdown/figures in `outputs/`

> Tip: Use a fixed `SEED` and save it in `outputs/metadata.json` for reproducibility.

---

### Stage 2 — Baselines + top-k explainability + stability/overlap
4. `notebooks/04_train_and_evaluate_baseline.ipynb`
5. `notebooks/05_stage2_topk_explainability.ipynb`

**Expected outputs (typical):**
- Models: `outputs/models/*`
- Metrics: `outputs/metrics/*.json`
- Explainability artifacts:
  - `top10_frequency_*.csv`
  - `semantic_group_frequency_*.csv`
  - `stability_summary.json`, `overlap_summary.json`
  - `semantic_stability_summary.json`, `semantic_overlap_summary.json`
  - `diversity_analysis.json`
  - `fig_top10_*.png`, `fig_semantic_groups_*.png`

**Reproduction check:**
- You should have both **LogReg** and **XGBoost** outputs.
- JSON summaries should be non-empty and match figures/tables referenced in `reports/`.

---

## Stage 3 — ZK-XIDS (Circom + Groth16) with scripts ✅
> You said you already have scripts. This section uses them directly.

Go to the ZK folder:
```bash
cd stage3_zk
```

### Stage 3.1 — Full pipeline (setup → input → circuit → proof → verify → benchmark)
#### 0) Setup
```bash
bash "scripts/stage 3.1/00_setup.sh"
```

#### 1) Prepare inputs (Python)
```bash
python "scripts/stage 3.1/01_prepare_input.py"
```

#### 2) Build circuit
- **Windows / PowerShell** (as your script indicates):
```powershell
powershell -ExecutionPolicy Bypass -File "scripts/stage 3.1/02_build_circuit.ps1"
```
- **Linux/macOS**: if you have an equivalent `.sh` build script, run it here.  
  (If not, keep using Windows for circuit build, then copy artifacts back.)

#### 3) Generate proof
```bash
bash "scripts/stage 3.1/03_generate_proof.sh"
```

#### 4) Verify proof
```bash
bash "scripts/stage 3.1/04_verify_proof.sh"
```

#### 5) Benchmark
```bash
python "scripts/stage 3.1/05_benchmark.py"
node "scripts/stage 3.1/benchmark_optimized.js"
```

**Expected outputs (examples you already have):**
- `proof_sample_*.json`, `public_sample_*.json`
- `benchmark_results.json`, `benchmark_optimized.json`

---

### Stage 3.2 — Generate/verify stage 3.2 proofs
Run the scripts inside `scripts/stage 3.2/` in the same order (setup → prepare → build → prove → verify → benchmark).  
**Expected outputs:**
- `proof_stage32_sample_*.json`, `public_stage32_sample_*.json`
- `benchmark_stage32.json`

---

### Stage 3.3 — Generate/verify stage 3.3 proofs
Run the scripts inside `scripts/stage 3.3/` in the same order.  
**Expected outputs:**
- `proof_stage33_sample_*.json`, `public_stage33_sample_*.json`
- `benchmark_stage33.json`

---

## Troubleshooting
- If `circom` is not found:
  - ensure `circom` is installed and available in PATH: `circom --version`
- If `snarkjs` is not found:
  - `npm i -g snarkjs` (or follow your local setup)
- If dataset is too large for local runs:
  - add a `SAMPLE_FRAC` option in notebooks/scripts (e.g., 0.05–0.20)
  - or run a subset of CSV files for reproduction

---

## Documentation
- Stage reports: `reports/`
- ZK outputs + scripts: `stage3_zk/`
- Final ZK summary (if present): `stage3_zk/reports/FINAL_SUMMARY.md`

---

## Repository Name Suggestion
**zk-xids-toniot**

---

## References
- TON_IoT Dataset: https://research.unsw.edu.au/projects/toniot-datasets
- Circom: https://docs.circom.io/
- Groth16: https://eprint.iacr.org/2016/260
