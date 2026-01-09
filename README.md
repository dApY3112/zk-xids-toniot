# ZK-XIDS: Zero-Knowledge Privacy-Preserving Intrusion Detection System

This repository contains the full code, data, and documentation for the Master's thesis project: **ZK-XIDS: Zero-Knowledge Privacy-Preserving Intrusion Detection System for Network Security**.

## Project Overview
- **Objective:** Develop a privacy-preserving IDS using zero-knowledge proofs (ZKP) to enable secure, explainable, and auditable network attack detection.
- **Dataset:** TON_IoT Network dataset (23 processed CSV files, 46 columns, ~22M rows)
- **Stages:**
  1. **Stage 1:** Data sanity check, stratified train/val/test split, leakage analysis
  2. **Stage 2:** Top-k explainability (LogReg, XGBoost, semantic grouping, stability analysis)
  3. **Stage 3:** ZK-XIDS implementation (Circom 2.1.9, Groth16, three circuit stages)

## Folder Structure
- `data/` — Raw and processed datasets
- `notebooks/` — Jupyter notebooks for data analysis, preprocessing, and model training
- `outputs/` — Model artifacts, splits, reports, and explainability results
- `reports/` — Markdown reports for each stage
- `stage3_zk/` — ZK-XIDS implementation, circuits, scripts, and final summary

## Key Features
- **Privacy-preserving inference** using ZKP
- **Explainable AI**: Top-k feature attribution, semantic grouping
- **Reproducible splits** and pipeline
- **Comprehensive documentation** for thesis defense

## How to Run
1. Install Python 3.10+, Conda recommended
2. Install dependencies from `requirements.txt` (if provided)
3. Run notebooks in order:
   - `01_data_sanity_check.ipynb`
   - `02_train_val_test_split.ipynb`
   - `03_preprocessing_pipeline.ipynb`
   - `04_train_and_evaluate_baseline.ipynb`
   - `05_stage2_topk_explainability.ipynb`
   - `06_stage3_prepare_artifacts.ipynb`
4. For ZK-XIDS, see `stage3_zk/README.md` and `stage3_zk/reports/FINAL_SUMMARY.md`

## Repository Name Suggestion
**zk-xids-toniot**

## References
- [TON_IoT Dataset](https://research.unsw.edu.au/projects/toniot-datasets)
- [Circom](https://docs.circom.io/)
- [Groth16](https://eprint.iacr.org/2016/260)

---
For questions or thesis defense, see the markdown reports in `reports/` and `stage3_zk/reports/`.
