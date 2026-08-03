# Stage 3 ZK-XIDS

This folder contains the zero-knowledge proof implementation for ZK-XIDS. It bridges the frozen 104-feature Logistic Regression model from the ML pipeline into Circom/Groth16 circuits.

## What Stage 3 Proves

Stage 3 proves statements about private processed network-flow features without revealing those feature values:

1. **Stage 3.1 - Inference only**
   - Proves that `y_hat` is the correct Logistic Regression prediction for a private 104-feature input.
2. **Stage 3.2 - Semantic groups**
   - Adds private aggregation of absolute feature contributions into 5 semantic groups.
3. **Stage 3.3 - Top-3 explanation**
   - Proves that the public `top3_ids` are the three highest-contribution semantic groups.
4. **Stage 3.4 - Exact SHAP top-3 explanation**
   - Proves that the public `top3_ids` are a valid ordered non-increasing top-3 semantic group ranking by absolute semantic-group Exact SHAP for the public Logistic Regression model.
   - Uses the closed-form Exact SHAP specialization for linear score models with fixed reference masking:
     `phi_g_int = sum_i w_int[i] * (x_int[i] - x_ref_int[i])`.
5. **Stage 3.5 - Optional input-commitment appendix prototype**
   - Extends the Stage 3.4 relation with a public Poseidon rolling commitment over `metadata_hash`, a private salt, and the private `x_shifted[104]` witness.
   - This is appendix evidence for possible log-row audit binding; it is not part of the main Stage 3.4 claim and still requires an external trusted commitment registry.

The semantic groups are:

| ID | Group | Size |
|---:|---|---:|
| 1 | Protocol | 3 |
| 2 | Application | 76 |
| 3 | ConnectionState | 13 |
| 4 | Ports | 2 |
| 5 | TrafficVolume | 10 |

Group sizes are defined by `artifacts/group_map.json`.

## Important Artifacts

| Path | Purpose |
|---|---|
| `artifacts/feature_order.json` | Frozen 104-feature order shared with the ML pipeline |
| `artifacts/group_map.json` | Feature-index to semantic-group mapping |
| `artifacts/model_public.json` | Quantized Logistic Regression weights, bias, and scales |
| `artifacts/bounds.json` | Bounds for shifted inputs and range checks |
| `test_vectors/test_sample_*.json` | TP, TN, and FN samples used for validation |
| `reports/LATEST_REPRO_REPORT.md` | Current authoritative ZK evidence report |
| `reports/zk_scaling_benchmark.md` | Repeated Stage 3.3 prove/verify benchmark |
| `reports/STAGE34_PROOF_REPORT.md` | Stage 3.4 Exact SHAP proof/verification evidence |
| `reports/STAGE34_BATCH_SMOKE_REPORT.md` | Supplemental Stage 3.4 30-sample witness/prove/verify smoke test |
| `reports/zk_stage34_scaling_benchmark.md` | Repeated Stage 3.4 prove/verify benchmark |
| `reports/STAGE35_INPUT_COMMITMENT_REPORT.md` | Appendix-only Stage 3.5 input-commitment prototype evidence |

## Current Source of Truth

Use `reports/LATEST_REPRO_REPORT.md` for current constraints, public/private signal counts, proof sizes, artifact sizes, and end-to-end harness timings.

Some older narrative reports contain historical optimized Node API timings. Those are useful optimization notes, but final thesis tables should use one timing protocol consistently.

## Run Commands

From `stage3_zk/`:

```powershell
npm run test:zk:quick
npm run test:zk
npm run test:zk:full
npm run evidence:zk:quick
npm run evidence:zk:full
npm run test:stage33:validate
npm run evidence:stage34
npm run compile:stage35
npm run evidence:stage35
```

From the repo root:

```powershell
python tools/reproduce.py zk --stage all --samples 1,2,3
python tools/reproduce.py zk --stage all --build --clean --prove --verify --report
python tools/reproduce.py zk-scale --stage 33 --sample 1 --runs 30 --warmup 2
python tools/reproduce.py stage34-batch-smoke --samples 30 --prove 30 --seed 34030
python tools/generate_model_registry.py
python tools/verify_stage34_policy.py --self-test
python tools/benchmark_stage34.py --sample 1 --runs 30 --warmup 2
```

## Circuit Map

| Stage | Circuit | Build scripts |
|---|---|---|
| 3.1 | `circuits/inference_only/inference_only.circom` | `scripts/stage 3.1/` |
| 3.2 | `circuits/semantic_groups/semantic_groups.circom` | `scripts/stage 3.2/` |
| 3.3 | `circuits/top3_explanation/top3_explanation.circom` | `scripts/stage 3.3/` |
| 3.4 | `circuits/exact_shap_top3/exact_shap_top3.circom` | `scripts/stage 3.4/` |
| 3.5 appendix | `circuits/exact_shap_top3_commitment/exact_shap_top3_commitment.circom` | `scripts/stage 3.5/` |

The preferred wrapper is `scripts/run_stage3_tests.py`; the per-stage scripts are kept for direct debugging.

## Latest Evidence Snapshot

From `reports/LATEST_REPRO_REPORT.md`:

| Stage | Constraints | Wires | Public Inputs | Private Inputs | Proof bytes | Public bytes |
|---:|---:|---:|---:|---:|---:|---:|
| 31 | 3,831 | 3,829 | 106 | 104 | 805 | 3,509 |
| 32 | 17,684 | 17,150 | 111 | 104 | 805 | 1,228 |
| 33 | 18,719 | 18,043 | 109 | 106 | 803 | 1,178 |

Stage 3.4 Exact SHAP proof evidence (`reports/STAGE34_PROOF_REPORT.md`):

| Stage | Constraints | Wires | Public Inputs | Private Inputs | Proof bytes | Public bytes |
|---:|---:|---:|---:|---:|---:|---:|
| 34 | 8,358 | 8,078 | 109 | 106 | 802-806 | 1,178 |

Supplemental Stage 3.4 batch smoke evidence (`reports/STAGE34_BATCH_SMOKE_REPORT.md`):

| Selected samples | Witness PASS | Prove PASS | Verify PASS | Public-output match |
|---:|---:|---:|---:|---:|
| 30 | 30 | 30 | 30 | 30 |

This batch is deterministic and label-balanced. It is functional smoke-test evidence and does not replace the authoritative proof-cost report above.

Stage 3.5 optional input-commitment appendix evidence (`reports/STAGE35_INPUT_COMMITMENT_REPORT.md`):

| Stage | Constraints | Wires | Public Inputs | Private Inputs | Public Outputs | Public Signals |
|---:|---:|---:|---:|---:|---:|---:|
| 35 appendix | 25,094 | 24,816 | 110 | 107 | 1 | 111 |

Stage 3.3 repeated benchmark (`reports/zk_scaling_benchmark.md`, 28 analyzed runs):

| Step | Mean ms | p50 ms | p95 ms |
|---|---:|---:|---:|
| prepare_input | 77 | 70 | 109 |
| witness_smoke | 87 | 78 | 150 |
| prove | 1,532 | 1,484 | 1,847 |
| verify | 588 | 562 | 696 |

## Security Tests

Stage 3.3 includes adversarial checks:

- `scripts/stage 3.3/test_wrong_explanation.py`
  - Swaps a true top-3 group with a non-top group; witness generation should fail.
- `scripts/stage 3.3/test_malicious_other2.py`
  - Tests duplicate, reused, and out-of-range private `other2_ids`; invalid witnesses should fail.
- `scripts/stage 3.3/validate_stage33.py`
  - Recomputes expected public top-3 groups from test vectors and proof public signals.
- `scripts/stage 3.4/test_stage34_negative.py`
  - Tests wrong prediction, wrong Exact SHAP top-3, duplicate/out-of-range group IDs, malicious remaining IDs, and private-input range violations.
- `scripts/stage 3.5/02_run_stage35_commitment.py`
  - Tests an appendix-only input commitment and verifies that tampering with the public commitment signal is rejected.

## Notes for Thesis Writing

- Although this repository implements the intrusion detection case study, the Stage 3.4 proof pattern should be described in the thesis as a scoped verifiable semantic explanation proof pattern for public linear/logistic tabular models under private inputs. The IDS-specific parts are the dataset, semantic group names, and evaluation setting.
- Avoid describing the main implementation as model-agnostic, confidential-model verification, differential privacy, or provenance-bound auditing. The Stage 3.5 input-commitment circuit is only an appendix prototype and still needs an external trusted commitment registry for a real provenance system.
- Final thesis claims should use the implemented public-model, private-input threat model.
- Model weights are public in the current proof design; the private value is the input feature vector.
- Model binding is handled by verifier policy / model registry checks over public artifacts, not by hidden-model commitment.
- Groth16 requires a circuit-specific trusted setup. The current setup is appropriate for a proof-of-concept; production deployment should use an MPC ceremony.
- Public outputs reveal `y_hat` and top-3 semantic group IDs. Processed input feature values and exact group contribution magnitudes remain private.
- Stage 3.4 uses non-strict `>=` ranking checks. Exact ties may admit multiple valid certified rankings; the witness generator uses smaller group ID as an off-circuit deterministic tie-break for reproducibility.
- Stage 3.4 verifies Exact SHAP only for the public Logistic Regression model with fixed reference masking. It does not implement confidential-model proofs, model-agnostic Exact SHAP verification, sumcheck/GKR, or Partition SHAP.
- For a thesis-facing discussion of public-model versus hidden-model variants, see `../reports/model_visibility_threat_model.md`.
- For verifier-side model binding, see `../reports/model_registry_and_verifier_policy.md`.
