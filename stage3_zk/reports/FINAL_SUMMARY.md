# ZK-XAI System Final Summary Report
## Verifiable Semantic Explanations Under Private Inputs

**Date**: January 7, 2026  
**Updated Feature Count**: **104 features** (upgraded from 87)  
**ZK Stack**: Circom 2.1.9, Groth16, snarkjs 0.7.5  

---

## Executive Summary

This report summarizes the original Stage 3.1-3.3 research prototype for zero-knowledge verifiable explanations under private inputs. The empirical instantiation is the ZK-XIDS intrusion detection case study, where a public Logistic Regression model is evaluated over private network-flow features.

The later Stage 3.4 semantic-group Exact SHAP extension is documented separately in:

- `stage3_zk/reports/STAGE34_PROOF_REPORT.md`
- `stage3_zk/reports/STAGE34_EXACT_SHAP_SUMMARY.md`
- `reports/stage34_thesis_integration.md`

Implemented Stage 3.1-3.3 components:

- **Stage 3.1**: Inference-only circuit for private-input Logistic Regression prediction.
- **Stage 3.2**: Semantic group explanation circuit using the original grouped linear attribution proxy.
- **Stage 3.3**: Top-3 verifiable explanation circuit for the original grouped attribution proxy.

Key achievement: the Stage 3 pipeline was upgraded from 87 to **104 features** while maintaining a reproducible, Windows-friendly end-to-end pipeline for build, witness generation, proving, and verification.

Authoritative measurements for Stage 3.1-3.3 are reported in:

- `stage3_zk/reports/LATEST_REPRO_REPORT.md`

---

## Performance Results

The reproducibility report includes:

- circuit complexity: constraints, wires, public inputs, and private inputs;
- communication cost: proof/public JSON sizes and number of public signals;
- end-to-end timings for build, witness, prove, and verify steps as invoked by the harness.

Key metrics from the latest reproducibility run:

- Proving time per sample is on the order of approximately `1.0-1.6s` across Stages 3.1-3.3 when invoked through the `snarkjs` CLI harness.
- Verification time per sample is on the order of approximately `0.5-0.8s` across Stages 3.1-3.3 when invoked through the same harness.

These are local wall-clock harness timings and include process/spawn overhead. They are useful for comparing stages within the same environment, not as hardware-independent performance guarantees.

---

## Technical Achievements

### Circuit Architecture

Feature scaling from 87 to 104 was completed by:

- updating hardcoded group mappings in the Stage 3 circuits;
- recalibrating bounds for the 104-feature Logistic Regression model;
- preserving shifted signed-integer encoding and range-check conventions.

Constraint counts and build artifact sizes are recorded in `LATEST_REPRO_REPORT.md`.

### Script Robustness

The Stage 3 scripts were hardened for reproducible local execution:

- Python scripts use `stage3_zk` as the project root.
- Artifact paths point consistently to `stage3_zk/artifacts/`.
- PowerShell and Bash scripts use robust relative path handling.
- Benchmark and evidence helpers report reproducible local timings.

### Validation and Negative Tests

The Stage 3.1-3.3 test vectors cover representative TP, TN, and FN samples. The validation checks show:

- proof generation succeeds for the valid test samples;
- proof verification succeeds for generated proofs;
- expected top-3 explanations match the circuit inputs;
- malformed explanation witnesses are rejected by dominance and group-ID constraints.

---

## Key Results by Stage

### Stage 3.1: Inference Only

- **Purpose**: prove correct Logistic Regression prediction without revealing the processed input features.
- **Current harness performance**: prove steps around `0.95-1.03s` and verify steps around `0.64-0.73s` in `LATEST_REPRO_REPORT.md`.
- **Security claim**: input-feature privacy and prediction authenticity.
- **Limitation**: no explanation relation.

### Stage 3.2: Semantic Group Explanation

- **Purpose**: compute semantic group contributions for the original grouped attribution proxy.
- **Current harness performance**: prove steps around `1.33-1.55s` and verify steps around `0.51-0.53s` in `LATEST_REPRO_REPORT.md`.
- **Explanation target**: five semantic groups: Protocol, Application, ConnectionState, Ports, TrafficVolume.
- **Limitation**: verifies an engineering attribution proxy rather than Exact SHAP.

### Stage 3.3: Top-3 Verifiable Explanation

- **Purpose**: verify that public top-3 semantic group IDs are authentic for the original grouped attribution proxy.
- **Current harness performance**: prove steps around `1.27-1.47s` and verify steps around `0.53-0.61s` in `LATEST_REPRO_REPORT.md`.
- **Security claim**: resistance to simple explanation manipulation attacks, such as claiming incorrect top-3 groups.
- **Output**: public top-3 group IDs; raw features and exact group values remain private.

---

## Sample Result

Stage 3.3 test sample 1:

```text
Input: TP_attack (y_true=1, y_pred=1)
Score: 390,139,428
Top-3: [2, 1, 5] = Application -> Protocol -> TrafficVolume

Group Contributions:
[1] Group 2 Application         : 2,404,909,056
[2] Group 1 Protocol            : 765,722,624
[3] Group 5 TrafficVolume       : 88,863,615
[4] Group 4 Ports               : 58,746,793
[5] Group 3 ConnectionState     : 57,540,608
```

This sample demonstrates the original Stage 3.3 grouped-attribution proof target. The Stage 3.4 Exact SHAP case studies are documented in `reports/stage34_case_studies.md`.

---

## Proof Pattern

The Stage 3 proof pattern is an applied cryptography mechanism for verifiable semantic explanations under private inputs:

1. Encode signed integer inputs and model parameters using shifted representations.
2. Prove the public prediction is computed from private input features and an approved public model.
3. Aggregate feature-level quantities into fixed semantic groups.
4. Verify a public top-k semantic explanation without revealing raw features.

The IDS-specific components are the TON_IoT dataset, the five IDS semantic group names, and the security-monitoring evaluation setting. The reusable pattern applies to compatible public linear/logistic tabular models with fixed semantic groups and a fixed reference or attribution rule.

---

## Security and Scope

### Threat Model Coverage

- **Input-feature privacy**: the verifier does not see raw processed features.
- **Prediction authenticity**: the proof binds the public prediction to the private input and public model.
- **Explanation authenticity**: the proof binds the public top-3 semantic groups to the same private input.
- **Intentional output disclosure**: the verifier learns `y_hat` and top-3 group IDs.

### Scope Boundaries

- The model is public in the implemented system.
- Hidden-model support is outside the selected public-model/private-input threat model.
- Input commitments are optional future work for provenance or cross-proof consistency, not a requirement for input privacy.
- Stage 3.1-3.3 verify the original grouped attribution proxy.
- Stage 3.4, documented separately, verifies semantic-group Exact SHAP for public Logistic Regression with fixed reference masking.
- The implementation is validated only in the IDS case study.

---

## Trade-Off Analysis

| Aspect | Stage 3.1 | Stage 3.2 | Stage 3.3 | Interpretation |
|---|---|---|---|---|
| Privacy | Input hidden | Input hidden | Input hidden | No raw feature disclosure |
| Explanation | None | Semantic groups | Verified top-3 groups | Progressive explanation authenticity |
| Proving time | ~1.0s | ~1.3-1.5s | ~1.3-1.5s | Additional explanation logic increases cost |
| Verification | ~0.64-0.73s | ~0.51-0.53s | ~0.53-0.61s | Same local CLI timing protocol |

The additional constraints for explanation authenticity are justified in an auditable SOC-style case study where the verifier needs confidence that the explanation summary is not client-supplied metadata.

---

## Research Prototype Deployment Considerations

### High-Level Flow

```text
Client / Prover                         SOC / Verifier
Capture or receive network flow   ->    Receive proof and public signals
Prepare private feature vector     ->    Check approved public model policy
Generate witness and proof         ->    Verify Groth16 proof
Send proof and public outputs      ->    Interpret y_hat and top-3 group IDs
```

### Scalability Notes

- **Single-threaded**: roughly `0.6-0.8` Stage 3.3 proofs/second under the current CLI harness timing.
- **Parallel proving**: the main scale-out path for higher throughput.
- **Verification**: cheaper than proving, though reported CLI timings include process overhead.

### Deployment Hardening

Production deployment would require additional engineering:

1. A multi-party ceremony for circuit-specific trusted setup.
2. Key management and verification-key versioning.
3. Verifier-side model-version binding through approved public artifacts.
4. Monitoring for proof generation and verification failures.

---

## Research Contributions

The thesis-facing contribution should be framed as:

- **C1**. A public-model/private-input framework for verifiable semantic explanations, instantiated on intrusion detection.
- **C2**. A semantic-group explanation abstraction that maps high-dimensional tabular features into human-readable groups.
- **C3**. A SNARK-verifiable semantic-group Exact SHAP top-3 method for public Logistic Regression with fixed reference masking, implemented in Stage 3.4.
- **C4**. A reproducible case-study evaluation covering IDS performance, explanation stability, proxy-vs-ExactSHAP comparison, proof cost, output leakage, reference sensitivity, model-version binding, and negative tests.

For the original Stage 3.1-3.3 system, the key contribution is the proof pattern for private-input inference and verifiable semantic top-k explanations. Stage 3.4 upgrades the explanation target to semantic-group Exact SHAP.

---

## Benchmark Pointers

```text
CURRENT AUTHORITATIVE BENCHMARK POINTERS (104 Features)
================================================================
Use stage3_zk/reports/LATEST_REPRO_REPORT.md for:
- constraints / wires / public-private input counts
- proof and public JSON sizes
- build, witness, prove, verify step status and timings

Use stage3_zk/reports/zk_scaling_benchmark.md for:
- repeated Stage 3.3 prove/verify p50 and p95 timings

Latest repeated Stage 3.3 benchmark:
- prove mean 1,532ms, p50 1,484ms, p95 1,847ms
- verify mean 588ms, p50 562ms, p95 696ms

Use stage3_zk/reports/zk_stage34_scaling_benchmark.md for:
- repeated Stage 3.4 witness/prove/verify timing evidence
================================================================
```

---

## Final Position

This repository should be read as a research prototype for a verifiable semantic explanation framework under private inputs, instantiated in a TON_IoT intrusion detection case study. The implementation demonstrates input-feature privacy, prediction authenticity, and explanation authenticity for the selected public-model/private-input setting. It does not claim production readiness, hidden-model support, model-agnostic SHAP verification, Partition SHAP, sumcheck/GKR, or XGBoost-in-ZK.

*Generated on January 7, 2026. Final timing claims should cite `LATEST_REPRO_REPORT.md`, `zk_scaling_benchmark.md`, and `zk_stage34_scaling_benchmark.md`.*
