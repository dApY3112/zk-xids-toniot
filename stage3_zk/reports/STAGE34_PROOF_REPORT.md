# Stage 3.4 Exact SHAP Proof Report

Generated: 2026-05-27T20:12:49+00:00 (UTC)

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
| vkey_bytes | 22669 |

## Results

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

## Limitations

- Public-model, private-input only; model confidentiality is not implemented.
- Model-agnostic verification, differential privacy, and input-provenance binding are not implemented in Stage 3.4.
- Exact SHAP verification is specialized to Logistic Regression with fixed reference masking.
- The reference vector is fixed by the circuit artifact; changing it requires a changed circuit/setup.
- Sumcheck/GKR, Partition SHAP, and XGBoost-in-ZK are not implemented.
