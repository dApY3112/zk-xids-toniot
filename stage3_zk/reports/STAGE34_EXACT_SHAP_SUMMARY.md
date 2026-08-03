# Stage 3.4 Exact SHAP Top-3 Verification - Implementation Status

Generated: 2026-05-22

## Scope

Stage 3.4 is a non-destructive extension of the existing ZK-XIDS Stage 3 pipeline. It targets SNARK verification of semantic-group Exact SHAP for the approved public Logistic Regression IDS model under the existing private-input setting. It is not a model-agnostic verifier and does not implement confidential-model support or differential privacy. Stage 3.4 does not implement input-provenance binding; that binding point is explored separately in the optional Stage 3.5 appendix prototype.

Current implementation status:

- Circuit source added: `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`
- Input generator added: `stage3_zk/scripts/stage 3.4/01_prepare_input_stage34.py`
- Compile helper added: `stage3_zk/scripts/stage 3.4/02_compile_circuit_stage34.ps1`
- Witness smoke helper added: `stage3_zk/scripts/stage 3.4/03_witness_smoke_stage34.py`
- Negative witness-test helper added: `stage3_zk/scripts/stage 3.4/test_stage34_negative.py`
- Prepared inputs generated for samples 1-8 under `stage3_zk/circuits/exact_shap_top3/build/`
- Circuit compile artifacts generated: `exact_shap_top3.r1cs`, `exact_shap_top3.sym`, and `exact_shap_top3_js/`
- Witness generation passed for samples 1-8.
- Negative witness tests passed for samples 1-8.
- Groth16 setup, proof generation, and verification passed for samples 1-8.
- Diverse test-vector report: `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md`
- Proof evidence report: `stage3_zk/reports/STAGE34_PROOF_REPORT.md`

## Mathematical Target

The circuit verifies the Logistic Regression closed-form specialization of semantic-group Exact SHAP under fixed reference masking:

```text
phi_g_int = sum_{i in G_g} w_int[i] * (x_int[i] - x_ref_int[i])
```

This is exactly equivalent to coalition-enumerated Exact SHAP for the LR score/logit because the model is linear and the reference vector is fixed. The Python evaluator verifies this equivalence before the circuit stage:

```text
Max enumeration-vs-closed-form SHAP difference: 2.842171e-14
```

## Reference Vector

The reference vector is the feature-wise training-set mean in processed feature space. It is exported in:

```text
stage3_zk/artifacts/exact_shap_reference.json
```

For Stage 3.4, `x_ref_int` is hardcoded in the circuit rather than accepted as prover-controlled input. This means the prover cannot choose a different reference vector inside the proof. If future work makes `x_ref` public input instead, the verifier must explicitly check it against the agreed reference artifact.

Because the reference vector is hardcoded into the compiled circuit, a "wrong reference vector" attack is not a witness-level input mutation in the current design. Changing the reference would require changing the circuit and trusted setup artifacts, so it is treated as a circuit/versioning concern rather than a negative witness test.

## Public and Private Signals

Public:

- `w_shifted[104]`
- `b_shifted`
- `y_hat`
- `top3_ids[3]`

Private:

- `x_shifted[104]`
- `other2_ids[2]`

The circuit does not publicly reveal processed input feature values or all `phi_g` values. It reveals only the prediction and claimed top-3 semantic group IDs.

## Circuit Checks

The Stage 3.4 circuit checks:

- `y_hat` is binary.
- shifted private inputs are in range.
- shifted public weights and bias are in range.
- LR score is computed from the same private input.
- public `y_hat` matches the sign of the LR score.
- semantic-group Exact SHAP values are computed with the fixed `x_ref_int`.
- ranking uses `abs(phi_g)`.
- top-3 IDs plus private remaining IDs form a permutation of `{1,2,3,4,5}`.
- claimed top-3 groups dominate the remaining two groups by absolute SHAP magnitude.
- claimed top-3 order is non-increasing by absolute SHAP magnitude.

## Prepared Sample Results

Stage 3.4 input generation succeeded for the original ZK test vectors and the expanded diverse vector set:

| Sample | Label | y_hat | Top-3 Exact SHAP groups |
|---:|---|---:|---|
| 1 | TP_attack | 1 | Application, ConnectionState, Protocol |
| 2 | TN_normal | 0 | ConnectionState, Protocol, TrafficVolume |
| 3 | FN_attack | 0 | Protocol, Application, ConnectionState |
| 4 | FP_normal | 1 | TrafficVolume, Protocol, ConnectionState |
| 5 | HighConf_attack | 1 | TrafficVolume, ConnectionState, Protocol |
| 6 | HighConf_normal | 0 | TrafficVolume, ConnectionState, Application |
| 7 | Borderline_score | 0 | Application, TrafficVolume, ConnectionState |
| 8 | SmallTop3Margin | 1 | ConnectionState, Protocol, Ports |

These rankings are based on `abs(phi_g_int)`, not the old Stage 3.3 `sum_i |w_i*x_i|` grouped attribution.

## Witness Test Status

Stage 3.4 witness generation has passed for all eight current ZK test vectors:

```text
PASS: Stage 3.4 witness generated: witness_sample_1.wtns
PASS: Stage 3.4 witness generated: witness_sample_2.wtns
PASS: Stage 3.4 witness generated: witness_sample_3.wtns
PASS: Stage 3.4 witness generated: witness_sample_4.wtns
PASS: Stage 3.4 witness generated: witness_sample_5.wtns
PASS: Stage 3.4 witness generated: witness_sample_6.wtns
PASS: Stage 3.4 witness generated: witness_sample_7.wtns
PASS: Stage 3.4 witness generated: witness_sample_8.wtns
```

Negative witness tests also passed for samples 1-8:

```text
PASS: negative case rejected as expected: wrong_y_hat
PASS: negative case rejected as expected: wrong_top3
PASS: negative case rejected as expected: duplicate_group_id
PASS: negative case rejected as expected: out_of_range_group_id
PASS: negative case rejected as expected: malicious_other2_reuses_top
PASS: negative case rejected as expected: private_input_range_violation
```

This means the Stage 3.4 circuit relation is satisfiable for valid inputs and rejects the main malformed witness cases at witness-generation time.

## Proof Verification Status

Groth16 proof generation and verification passed for all eight current ZK test vectors:

| Sample | Witness ms | Prove ms | Verify ms | Proof bytes | Public bytes | Status |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 64 | 1280 | 711 | 805 | 1178 | PASS |
| 2 | 58 | 1248 | 817 | 800 | 1178 | PASS |
| 3 | 63 | 1009 | 630 | 806 | 1178 | PASS |
| 4 | 65 | 1365 | 915 | 807 | 1178 | PASS |
| 5 | 72 | 1102 | 618 | 802 | 1178 | PASS |
| 6 | 60 | 1085 | 618 | 806 | 1178 | PASS |
| 7 | 59 | 1029 | 639 | 805 | 1178 | PASS |
| 8 | 61 | 1033 | 657 | 805 | 1178 | PASS |

Circuit and artifact metrics:

| Metric | Value |
|---|---:|
| Constraints | 8358 |
| Wires | 8078 |
| Public Inputs | 109 |
| Private Inputs | 106 |
| R1CS bytes | 1283048 |
| WASM bytes | 99582 |
| ZKey bytes | 4573072 |
| Verification key bytes | 22669 |
| Public signals | 109 |

## Claims and Non-Claims

Current correct claim:

> Stage 3.4 implements and verifies a SNARK relation for semantic-group Exact SHAP specialized to public Logistic Regression. Valid witnesses, Groth16 proof generation, and proof verification pass for the eight current ZK test vectors, and malformed explanation/prediction/group-ID inputs are rejected at witness-generation time.

Do not claim:

- model-agnostic verification.
- Sumcheck/GKR support.
- Partition SHAP support.
- confidential-model support.
- model-agnostic Exact SHAP verification for arbitrary models.
- differential privacy.
- full input-provenance binding to a specific SIEM event or log row; Stage 3.5 is only an appendix prototype of the commitment check.

Reproducibility command:

```powershell
python tools/reproduce.py zk-stage34 --samples 1,2,3,4,5,6,7,8
```
