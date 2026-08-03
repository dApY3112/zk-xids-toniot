# Stage 3.4 Batch Smoke-Test Report

Generated: 2026-06-17T09:11:55+00:00 (UTC)

## Purpose

This supplemental smoke test runs the current Stage 3.4 witness/prove/verify path on a deterministic label-balanced batch from the processed test split. It complements the eight curated Stage 3.4 vectors; it does not replace the authoritative proof report or the full ML evaluation.

## Configuration

| Item | Value |
|---|---:|
| requested_samples | 30 |
| proved_samples | 30 |
| seed | 34030 |
| curated_vector_files | 8 |
| excluded_curated_rows_with_metadata | 5 |
| candidate_normals | 18010 |
| candidate_attacks | 484601 |
| temporary_artifacts_retained | False |

## Summary

| Metric | Value |
|---|---:|
| selected_samples | 30 |
| witness_pass | 30 |
| prove_pass | 30 |
| verify_pass | 30 |
| public_output_match_pass | 30 |
| failures | 0 |

## Classification Counts In Batch

| TN | FP | FN | TP |
|---:|---:|---:|---:|
| 15 | 0 | 0 | 15 |

## Timing Summary

| Step | Count | Min ms | Median ms | Mean ms | Max ms |
|---|---:|---:|---:|---:|---:|
| witness | 30 | 64 | 74.0 | 107.267 | 934 |
| prove | 30 | 1111 | 1237.5 | 1338.3 | 2403 |
| verify | 30 | 667 | 745.5 | 771.7 | 1072 |

## Sample Results

| Batch ID | Test row | Dataset index | y_true | y_hat | Public top-3 groups | Witness | Prove | Verify | Public signals | Public match |
|---:|---:|---:|---:|---:|---|---|---|---|---:|---|
| 1 | 303781 | 2676229 | 1 | 1 | ConnectionState, Protocol, TrafficVolume | PASS | PASS | PASS | 109 | True |
| 2 | 97286 | 1318806 | 0 | 0 | Protocol, Application, ConnectionState | PASS | PASS | PASS | 109 | True |
| 3 | 58622 | 2179466 | 0 | 0 | ConnectionState, Protocol, TrafficVolume | PASS | PASS | PASS | 109 | True |
| 4 | 395029 | 256025 | 0 | 0 | TrafficVolume, ConnectionState, Protocol | PASS | PASS | PASS | 109 | True |
| 5 | 74162 | 2157 | 0 | 0 | Protocol, ConnectionState, Application | PASS | PASS | PASS | 109 | True |
| 6 | 372618 | 1961576 | 0 | 0 | Protocol, Ports, ConnectionState | PASS | PASS | PASS | 109 | True |
| 7 | 479442 | 2099167 | 1 | 1 | Application, ConnectionState, Protocol | PASS | PASS | PASS | 109 | True |
| 8 | 138475 | 2216171 | 1 | 1 | ConnectionState, Protocol, TrafficVolume | PASS | PASS | PASS | 109 | True |
| 9 | 108749 | 168325 | 0 | 0 | TrafficVolume, ConnectionState, Protocol | PASS | PASS | PASS | 109 | True |
| 10 | 482799 | 293283 | 0 | 0 | TrafficVolume, Application, Ports | PASS | PASS | PASS | 109 | True |
| 11 | 441893 | 2942713 | 1 | 1 | ConnectionState, Ports, Protocol | PASS | PASS | PASS | 109 | True |
| 12 | 384883 | 4527 | 0 | 0 | Protocol, Application, ConnectionState | PASS | PASS | PASS | 109 | True |
| 13 | 303384 | 138618 | 1 | 1 | Ports, ConnectionState, Protocol | PASS | PASS | PASS | 109 | True |
| 14 | 97059 | 2216070 | 0 | 0 | Protocol, Application, ConnectionState | PASS | PASS | PASS | 109 | True |
| 15 | 365373 | 2062337 | 1 | 1 | Application, ConnectionState, Protocol | PASS | PASS | PASS | 109 | True |
| 16 | 254316 | 793229 | 1 | 1 | ConnectionState, Protocol, Application | PASS | PASS | PASS | 109 | True |
| 17 | 358093 | 608034 | 1 | 1 | ConnectionState, Protocol, Application | PASS | PASS | PASS | 109 | True |
| 18 | 394930 | 1712305 | 1 | 1 | Ports, ConnectionState, Protocol | PASS | PASS | PASS | 109 | True |
| 19 | 331391 | 2003792 | 1 | 1 | Protocol, Application, ConnectionState | PASS | PASS | PASS | 109 | True |
| 20 | 427698 | 2186305 | 0 | 0 | Protocol, ConnectionState, Application | PASS | PASS | PASS | 109 | True |
| 21 | 301041 | 1716566 | 1 | 1 | ConnectionState, Protocol, Application | PASS | PASS | PASS | 109 | True |
| 22 | 103302 | 2127066 | 1 | 1 | Application, ConnectionState, Protocol | PASS | PASS | PASS | 109 | True |
| 23 | 92517 | 6758 | 0 | 0 | ConnectionState, Protocol, TrafficVolume | PASS | PASS | PASS | 109 | True |
| 24 | 243761 | 2642850 | 0 | 0 | Protocol, ConnectionState, Application | PASS | PASS | PASS | 109 | True |
| 25 | 346449 | 3297379 | 0 | 0 | TrafficVolume, ConnectionState, Protocol | PASS | PASS | PASS | 109 | True |
| 26 | 245063 | 595194 | 1 | 1 | ConnectionState, Protocol, Application | PASS | PASS | PASS | 109 | True |
| 27 | 353685 | 2198509 | 0 | 0 | ConnectionState, Ports, Protocol | PASS | PASS | PASS | 109 | True |
| 28 | 256390 | 2298853 | 0 | 0 | Protocol, ConnectionState, Ports | PASS | PASS | PASS | 109 | True |
| 29 | 71100 | 1286048 | 1 | 1 | ConnectionState, Protocol, Application | PASS | PASS | PASS | 109 | True |
| 30 | 384646 | 1704176 | 1 | 1 | ConnectionState, Protocol, TrafficVolume | PASS | PASS | PASS | 109 | True |

## Limitations

- The batch is deterministic and label-balanced, not a statistical reliability estimate for the full test split.
- Proof success means the circuit relation was satisfied for the selected witnesses; it does not imply ground-truth correctness.
- The report intentionally omits private feature vectors, full witness files, proof JSON, and public-signal JSON.
- The authoritative Stage 3.4 proof-cost numbers remain in `stage3_zk/reports/STAGE34_PROOF_REPORT.md`.
