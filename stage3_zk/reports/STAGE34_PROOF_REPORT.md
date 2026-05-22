# Stage 3.4 Exact SHAP Proof Report

Generated: 2026-05-22T14:47:01+00:00 (UTC)

## Claim

Stage 3.4 verifies semantic-group Exact SHAP top-3 authenticity for the public Logistic Regression model under private input features. The circuit uses the closed-form Exact SHAP specialization for a linear score model with a fixed public reference vector hardcoded in the circuit.

## Circuit Stats

| Metric | Value |
|---|---:|
| Constraints | 8358 |
| Wires | 8078 |
| Public Inputs | 109 |
| Private Inputs | 106 |
| Labels | 9459 |
| Outputs | 0 |

## Artifact Sizes

| Artifact | Bytes |
|---|---:|
| r1cs_bytes | 1283048 |
| wasm_bytes | 99582 |
| zkey_bytes | 4573072 |
| vkey_bytes | 22671 |

## Results

| Sample | Witness ms | Prove ms | Verify ms | Proof bytes | Public bytes | Public signals | Status |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 80 | 1090 | 672 | 802 | 1178 | 109 | PASS |
| 2 | 63 | 1083 | 605 | 806 | 1178 | 109 | PASS |
| 3 | 61 | 1006 | 605 | 803 | 1178 | 109 | PASS |

## Limitations

- Public-model, private-input only; model confidentiality is not implemented.
- Exact SHAP verification is specialized to Logistic Regression with fixed reference masking.
- The reference vector is fixed by the circuit artifact; changing it requires a changed circuit/setup.
- Sumcheck/GKR and Partition SHAP are not implemented.
