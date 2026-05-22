# ZK Scaling Benchmark (Repeated Prove/Verify)
Generated: 2026-02-12T20:17:23+00:00 (UTC)

## Configuration
- Stage: `33`
- Sample: `1`
- Runs (total): `30`
- Warmup (excluded): `2`
- Runs analyzed: `28`

## Environment (from harness report)
- Python: 3.10.19 (C:\Anaconda\envs\py310\python.exe)
- Node: v20.12.2 (npm 10.8.3)
- snarkjs: snarkjs@0.7.5

## Timing summary (ms)
Each row is summarized across runs: min/mean/p50/p95/max (std shown separately).

| Step | n | min | mean | p50 | p95 | max | std |
|---|---:|---:|---:|---:|---:|---:|---:|
| wall_total | 28 | 4217 | 4813 | 4724 | 5532 | 5767 | 373 |
| prepare_input | 28 | 46 | 77 | 70 | 109 | 141 | 21 |
| witness_smoke | 28 | 61 | 87 | 78 | 150 | 219 | 33 |
| prove | 28 | 1313 | 1532 | 1484 | 1847 | 2078 | 174 |
| verify | 28 | 515 | 588 | 562 | 696 | 921 | 79 |

## Communication (bytes)
From the circuit stats (sizes are stable across runs).

| Artifact | Size (bytes) |
|---|---:|
| r1cs_bytes | 2927208 |
| wasm_bytes | 137026 |
| zkey_bytes | 10088775 |
| vkey_bytes | 22685 |
| proof_bytes | 806 |
| public_bytes | 1178 |
| n_public_signals | 109 |
| constraints | 18719 |
