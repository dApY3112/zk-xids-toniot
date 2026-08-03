# Stage 3.5 Input Commitment Prototype Report

Generated: 2026-05-28T12:17:38+00:00 (UTC)

## Status

This is an optional appendix prototype, not part of the main Stage 3.4 claim. It adds a public Poseidon rolling commitment over the private input vector, a private salt, and a public metadata hash. A deployment would bind a proof to a concrete log row by comparing the public `input_commitment` signal against a commitment registered at ingestion time.

## Circuit Delta

| Metric | Stage 3.4 | Stage 3.5 Prototype |
|---|---:|---:|
| Constraints | 8358 | 25094 |
| Wires | 8078 | 24816 |
| Public Inputs | 109 | 110 |
| Private Inputs | 106 | 107 |
| Outputs | 0 | 1 |

Constraint overhead vs Stage 3.4: 3.0x.

## Artifact Sizes

| Artifact | Bytes |
|---|---:|
| r1cs_bytes | 4236604 |
| wasm_bytes | 4174756 |
| zkey_bytes | 11408750 |
| vkey_bytes | 23052 |

## Proof Results

| Sample | Witness ms | Prove ms | Verify ms | Tampered Commitment Rejected | Public Signals | Proof Bytes |
|---:|---:|---:|---:|---|---:|---:|
| 1 | 541 | 2217 | 690 | yes | 111 | 806 |
| 7 | 399 | 2972 | 1647 | yes | 111 | 807 |
| 8 | 817 | 3002 | 786 | yes | 111 | 803 |

## Timing Summary

| Metric | Stage 3.4 Mean | Stage 3.5 Mean |
|---|---:|---:|
| Witness ms | 62.8 | 585.7 |
| Prove ms | 1143.9 | 2730.3 |
| Verify ms | 700.6 | 1041.0 |

## Interpretation

- The prototype closes the narrow `some private witness` gap only when an external system stores the same public commitment at ingestion time.
- It does not authenticate SIEM provenance by itself; the verifier must compare public signal 0 to a trusted commitment registry entry.
- It does not add differential privacy or model confidentiality. The public values remain `input_commitment`, `metadata_hash`, `y_hat`, and `top3_ids`.
- The measured overhead is large enough that this should stay in the appendix unless the thesis needs a stronger provenance story.
