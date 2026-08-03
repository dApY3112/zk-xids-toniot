# Stage 3.4 Thesis Integration: Verified Semantic-Group Exact SHAP

Generated: 2026-05-27T20:13:47+00:00 (UTC)

## Thesis Claim

This thesis proposes a scoped public-model/private-input proof pattern for verifiable semantic explanations under private inputs. The pattern is instantiated in an intrusion detection case study, where an approved public Logistic Regression model classifies private network-flow features and Stage 3.4 verifies a valid ordered non-increasing top-3 semantic-group Exact SHAP explanation. This upgrades Stage 3.3's engineering attribution proxy (`sum_i |w_i*x_i|`) to a game-theoretically grounded explanation target while preserving the Circom/Groth16 proof stack.

The implemented main claim is intentionally narrow: it targets public linear/logistic tabular models with fixed semantic groups and a fixed reference vector. It is not a model-agnostic XAI verifier, does not hide model weights, and does not provide differential privacy. Stage 3.4 does not bind the private witness to a specific external event by itself; an optional Stage 3.5 appendix prototype evaluates an input-commitment layer for that audit-binding use case.

## Research Questions

- RQ1: Can public linear/logistic tabular inference be verified without revealing processed features in an IDS instantiation?
- RQ2: Can semantic explanations be verified cryptographically rather than trusted as client-supplied metadata?
- RQ3: Can semantic-group Exact SHAP be made feasible in a SNARK for an approved public Logistic Regression model?
- RQ4: What overhead and limitations arise when moving from an engineering attribution proxy to verified Exact SHAP in the intrusion detection case study?

## Contribution Framing

- C1. A public-model/private-input proof pattern for verifiable semantic explanations over public linear/logistic tabular models, instantiated on intrusion detection.
- C2. A semantic-group explanation abstraction that maps high-dimensional tabular features into human-readable groups.
- C3. A SNARK-verifiable semantic-group Exact SHAP top-3 method for public Logistic Regression with fixed reference masking.
- C4. A reproducible case-study evaluation covering IDS performance, explanation stability, proxy-vs-ExactSHAP comparison, proof cost, output leakage, reference sensitivity, model-version binding, negative tests, and an appendix-only input-commitment feasibility prototype.

## Generalization Scope: Proof Pattern vs. IDS Instantiation

| Layer | IDS-specific in this repository | Reusable beyond IDS |
|---|---|---|
| Dataset/task | TON_IoT, Normal vs Attack | Tabular private-input classification tasks with an approved public linear/logistic model and fixed semantic groups |
| Semantic groups | Protocol, Application, ConnectionState, Ports, TrafficVolume | Fixed human-meaningful feature groups |
| Model | Logistic Regression IDS model | Approved public linear/logistic models |
| Explanation | Semantic-group Exact SHAP over IDS groups | Semantic-group Exact SHAP over fixed groups |
| Proof relation | Groth16 proof for IDS artifacts | Same proof pattern with new artifacts for compatible public linear/logistic models |
| Evaluation | IDS metrics, FPR, SOC triage | Domain-specific metrics in other applications |

The implementation is validated only on the IDS case study. The Stage 3.4 relation itself is not inherently IDS-specific: it verifies a public linear/logistic score, a fixed reference vector, fixed semantic groups, and a top-3 semantic explanation computed from the same private input. Generalization to other domains requires replacing the feature schema, semantic group map, reference vector, approved public model artifact, circuit artifacts, and evaluation metrics.

## Method Justification

The explanation players are the five semantic groups used throughout the project: Protocol, Application, ConnectionState, Ports, and TrafficVolume. The Exact SHAP value function is the LR score/logit, not probability. Removed groups are replaced with the feature-wise training-set mean in processed feature space.

For this public LR model, coalition-enumerated semantic-group Exact SHAP has the exact closed form:

```text
phi_g(x) = sum_{i in G_g} w_i * (x_i - x_ref_i)
```

The Python evaluator verifies this equivalence numerically: max enumeration-vs-closed-form difference `2.842171e-14`. Stage 3.4 proves the quantized integer form of this relation inside Groth16:

```text
phi_g_int = sum_{i in G_g} w_int[i] * (x_int[i] - x_ref_int[i])
```

For the formal relation, protocol construction, theorem statements, proof sketches, and leakage boundaries, see `reports/formal_framework_and_security_guarantees.md`.

## Stage 3.1-3.4 Comparison

Stages 3.1-3.3 use the latest reproducibility report; Stage 3.4 uses `stage3_zk/reports/STAGE34_PROOF_REPORT.md`.

| Stage | Verified relation | Explanation target | Constraints | Wires | Public | Private | R1CS bytes | ZKey bytes | Proof bytes | Public bytes | Prove ms | Verify ms |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3.1 | LR inference only | None | 3,831 | 3,829 | 106 | 104 | 597,816 | 1,938,424 | 801-805 (mean 803) | 3509-3509 (mean 3509) | 953-1030 (mean 984) | 641-733 (mean 677) |
| 3.2 | LR inference + old semantic aggregation | Old proxy: sum_i abs(w_i*x_i) per semantic group | 17,684 | 17,150 | 111 | 104 | 2,770,124 | 9,683,997 | 802-806 (mean 804) | 1228-1231 (mean 1230) | 1328-1546 (mean 1406) | 514-531 (mean 520) |
| 3.3 | LR inference + old grouped-attribution top-3 | Top-3 old grouped linear attribution proxy | 18,719 | 18,043 | 109 | 106 | 2,927,208 | 10,088,775 | 803-808 (mean 805) | 1178-1178 (mean 1178) | 1266-1468 (mean 1385) | 531-608 (mean 577) |
| 3.4 | LR inference + semantic-group Exact SHAP top-3 | Top-3 semantic-group Exact SHAP by abs(phi_g) | 8,358 | 8,078 | 109 | 106 | 1,283,048 | 4,573,072 | 800-807 (mean 804) | 1178-1178 (mean 1178) | 1009-1365 (mean 1144) | 618-915 (mean 701) |

## Correctness Evidence

- Python coalition enumeration equals closed-form LR Exact SHAP: max difference `2.842171e-14`.
- Stage 3.4 valid witnesses pass for samples 1-8.
- Stage 3.4 Groth16 proof generation and verification pass for samples 1-8.
- Stage 3.4 negative witness tests reject malformed inputs for samples 1-8.
- The extended Stage 3.4 vector set adds FP, high-confidence attack, high-confidence normal, borderline-score, and near-tie ranking cases; see `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md`.
- Float-vs-quantized LR agreement check: val: prediction agreement 99.991246% (44/502628 mismatches), ordered top-3 match 93.855694%, mean overlap 2.9452/3; test: prediction agreement 99.994230% (29/502628 mismatches), ordered top-3 match 93.817495%, mean overlap 2.9449/3. See `reports/float_vs_quantized_lr_agreement.md`.
- The proof binds `y_hat` and a valid non-increasing Exact SHAP top-3 group ranking to the same private shifted input vector.
- The optional Stage 3.5 appendix prototype adds a public input commitment and rejects tampered commitment public signals for samples 1, 7, and 8. See `reports/input_commitment_appendix.md`.

## Ranking and Tie-Breaking

Stage 3.4 verifies that the public top-3 semantic group IDs are distinct, valid group IDs and that their absolute Exact SHAP magnitudes are ordered non-increasingly and dominate the two remaining groups. The circuit uses `>=` comparisons, so exact ties can admit multiple valid certified rankings. The witness generator sorts ties deterministically by smaller group ID for reproducibility, but that secondary tie-break is not enforced inside the current circuit. A deployment requiring a unique canonical ranking would need an additional lexicographic tie-break constraint.

## Negative Tests

Stage 3.4 rejects malformed witnesses for:

- wrong prediction (`y_hat`)
- wrong Exact SHAP top-3 IDs
- duplicate group IDs
- out-of-range group IDs
- malicious `other2_ids` reusing top groups
- private input range violation

`x_ref_int` is hardcoded in the Stage 3.4 circuit, so a wrong reference vector is not accepted as a prover-controlled witness value. Changing the reference would require changing the circuit/setup artifact.

## Proxy-vs-ExactSHAP Result

The old Stage 3.3 grouped linear attribution remains useful as a cheap engineering baseline, but it is not a Shapley-value explanation. Offline comparison over 1100 reconstructed Stage 2 samples shows mean top-3 overlap `2.0618 / 3` and mean Jaccard overlap `0.5407`. The old proxy is dominated by the large Application group, while Exact SHAP more often emphasizes ConnectionState and Protocol as marginal semantic contributors relative to the reference input.

## Case Studies

See `reports/stage34_case_studies.md` for three thesis-ready examples: a true positive attack, a true negative normal sample, and a false negative attack.

## Model Visibility and Scope

The implemented threat model is public-model, private-input. This is suitable for auditable IDS/SOC settings where the verifier should know the detector being certified, while the sensitive object is the network-flow input. It does not address model-IP protection. A hidden-model extension would require a model commitment, for example proving `C_model = Poseidon(w, b, x_ref, salt)` while keeping `w`, `b`, and `x_ref` private. The current thesis can present that as future work, not as an implemented claim. See `reports/model_visibility_threat_model.md`.

## Verifier Acceptance Policy

For Stage 3.4, proof verification should be paired with a verifier-side model policy. The verifier accepts only if the verification key corresponds to the approved Stage 3.4 circuit, the public LR weights and bias match the approved `model_public.json`, the feature order, group map, bounds, and Exact SHAP reference vector match the registered artifacts, the registry digest identifies the approved model version, and the Groth16 proof verifies. See `reports/model_registry_and_verifier_policy.md`.

## Output Leakage

The circuit hides processed input feature values and the exact semantic-group SHAP values. It intentionally reveals `y_hat` and the top-3 semantic group IDs because these are the certified IDS decision and explanation summary. The resulting privacy claim is input-feature privacy under the zero-knowledge property of Groth16, parameterized by an explicit leakage function consisting of the approved public model/version metadata, `y_hat`, and `top3_ids`. It is not complete behavioral secrecy and it is not differential privacy, since the current system does not add noise to the disclosed outputs. See `reports/stage34_output_leakage_audit.md` for a distributional audit of these public outputs.

## Input Provenance and Audit Binding

Stage 3.4 proves that the public prediction and top-3 semantic explanation are consistent with the same private witness. It does not, by itself, prove that the witness came from a specific external log row or previously registered event.

The optional Stage 3.5 appendix prototype demonstrates one feasible extension: it computes a public Poseidon rolling commitment over `(domain_tag, metadata_hash, salt, x_shifted[104])`. In the generated evidence, valid proofs verify and tampering with the public commitment signal is rejected. This should be described as a provenance binding point, not as a complete SIEM provenance system, because a real deployment must also store and trust the ingestion-time commitment registry. See `reports/input_commitment_appendix.md` and `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md`.

## Reference Sensitivity

The implemented Stage 3.4 circuit fixes the training-mean reference vector. Alternative reference vectors are not additional ZK claims, but an offline sensitivity analysis is useful for critical self-assessment. See `reports/exact_shap_reference_sensitivity.md`.

## Ranking Stability

The proof verifies correctness of the claimed ranking for one private input; it does not prove that the explanation is stable under nearby inputs. For Logistic Regression, each group SHAP value is linear in the input, so perturbation sensitivity can be bounded by the group weight norm. This supports an optional margin-based robustness analysis, but it is not implemented as a ZK claim in the current repository. The empirical rank-3 vs rank-4 margin analysis reports val: median margin 0.044013, p5 0.000411, <=0.001 in 11.1723%; test: median margin 0.044013, p5 0.000411, <=0.001 in 11.0802%; see `reports/exact_shap_ranking_margin.md`.

## Critical Self-Assessment

Stage 3.4 strengthens the thesis contribution, but the scope remains intentionally narrow. The model is public, only the input is private, and the verified Exact SHAP relation is specific to Logistic Regression with fixed reference masking. The system does not provide model-agnostic verification, confidential-model support, differential privacy, arbitrary-model Exact SHAP, Partition SHAP, or sumcheck/GKR. Input-provenance binding is only explored as an appendix Stage 3.5 prototype and still depends on an external trusted commitment registry. The binary IDS task also remains constrained by the Logistic Regression accuracy trade-off relative to the stronger XGBoost plaintext baseline.

## Thesis-Ready Conclusion

The final Stage 3.4 result is not merely an additional circuit: it changes the verified explanation target from an engineering proxy to semantic-group Exact SHAP, while keeping proof generation practical through a mathematically justified closed form for linear models. This provides a clear research contribution and a defensible path for future work on larger models and scalable SHAP verification.
