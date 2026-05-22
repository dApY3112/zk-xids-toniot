# Stage 3.4 Repeated Prove/Verify Benchmark

Generated: 2026-05-22T15:27:28+00:00 (UTC)

This report benchmarks the implemented Stage 3.4 Exact SHAP circuit on repeated runs for one fixed test sample. It is timing evidence only; it does not change the circuit, model, proof relation, or benchmark numbers in other reports.

- Sample: `1`
- Warmup runs: `2`
- Analyzed runs: `30`
- Proof system: Circom + Groth16 via repository-local snarkjs CLI

| Step | Mean ms | Median ms | p95 ms | Min ms | Max ms |
|---|---:|---:|---:|---:|---:|
| witness | 83 | 65 | 188 | 60 | 281 |
| prove | 1327 | 1251 | 2038 | 1002 | 3141 |
| verify | 739 | 662 | 1194 | 580 | 1246 |

## Artifact Stability

- Proof bytes range: `802-808`
- Public bytes range: `1178-1178`
- Public signal count: `[109]`

## Thesis Interpretation

Stage 3.4 adds verified semantic-group Exact SHAP top-3 authenticity while keeping proof sizes small and verification substantially cheaper than proving under this CLI harness. These measurements should be reported as local prototype evidence, not as a hardware-independent performance guarantee.
