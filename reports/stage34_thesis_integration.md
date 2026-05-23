# Stage 3.4 Thesis Integration: Verified Semantic-Group Exact SHAP

Generated: 2026-05-22T15:27:41+00:00 (UTC)

## Thesis Claim

This thesis proposes a zero-knowledge framework for verifiable semantic explanations under private inputs. The framework is instantiated in an intrusion detection case study, where a public Logistic Regression model classifies private network-flow features and Stage 3.4 verifies the ordered top-3 semantic-group Exact SHAP explanation. This upgrades Stage 3.3's engineering attribution proxy (`sum_i |w_i*x_i|`) to a game-theoretically grounded explanation target while preserving the Circom/Groth16 proof stack.

## Research Questions

- RQ1: Can private-input tabular inference be verified without revealing processed features in an IDS instantiation?
- RQ2: Can semantic explanations be verified cryptographically rather than trusted as client-supplied metadata?
- RQ3: Can semantic-group Exact SHAP be made feasible in a SNARK for an approved public Logistic Regression model?
- RQ4: What overhead and limitations arise when moving from an engineering attribution proxy to verified Exact SHAP in the intrusion detection case study?

## Contribution Framing

- C1. A public-model/private-input framework for verifiable semantic explanations, instantiated on intrusion detection.
- C2. A semantic-group explanation abstraction that maps high-dimensional tabular features into human-readable groups.
- C3. A SNARK-verifiable semantic-group Exact SHAP top-3 method for public Logistic Regression with fixed reference masking.
- C4. A reproducible case-study evaluation covering IDS performance, explanation stability, proxy-vs-ExactSHAP comparison, proof cost, output leakage, reference sensitivity, model-version binding, and negative tests.

## Generalization Scope: Framework vs. IDS Instantiation

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

## Stage 3.1-3.4 Comparison

Stages 3.1-3.3 use the latest reproducibility report; Stage 3.4 uses `stage3_zk/reports/STAGE34_PROOF_REPORT.md`.

| Stage | Verified relation | Explanation target | Constraints | Wires | Public | Private | R1CS bytes | ZKey bytes | Proof bytes | Public bytes | Prove ms | Verify ms |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 3.1 | LR inference only | None | 3,831 | 3,829 | 106 | 104 | 597,816 | 1,938,424 | 801-805 (mean 803) | 3509-3509 (mean 3509) | 953-1030 (mean 984) | 641-733 (mean 677) |
| 3.2 | LR inference + old semantic aggregation | Old proxy: sum_i abs(w_i*x_i) per semantic group | 17,684 | 17,150 | 111 | 104 | 2,770,124 | 9,683,997 | 802-806 (mean 804) | 1228-1231 (mean 1230) | 1328-1546 (mean 1406) | 514-531 (mean 520) |
| 3.3 | LR inference + old grouped-attribution top-3 | Top-3 old grouped linear attribution proxy | 18,719 | 18,043 | 109 | 106 | 2,927,208 | 10,088,775 | 803-808 (mean 805) | 1178-1178 (mean 1178) | 1266-1468 (mean 1385) | 531-608 (mean 577) |
| 3.4 | LR inference + semantic-group Exact SHAP top-3 | Top-3 semantic-group Exact SHAP by abs(phi_g) | 8,358 | 8,078 | 109 | 106 | 1,283,048 | 4,573,072 | 802-806 (mean 804) | 1178-1178 (mean 1178) | 1006-1090 (mean 1060) | 605-672 (mean 627) |

## Correctness Evidence

- Python coalition enumeration equals closed-form LR Exact SHAP: max difference `2.842171e-14`.
- Stage 3.4 valid witnesses pass for test samples 1, 2, and 3.
- Stage 3.4 Groth16 proof generation and verification pass for test samples 1, 2, and 3.
- The proof binds `y_hat` and Exact SHAP top-3 IDs to the same private shifted input vector.

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

For Stage 3.4, proof verification should be paired with a verifier-side model policy. The verifier accepts only if the verification key corresponds to the approved Stage 3.4 circuit, the public LR weights and bias match the approved `model_public.json`, the feature order, group map, bounds, and Exact SHAP reference vector match the registered artifacts, the registry digest identifies the approved public model version, and the Groth16 proof verifies. See `reports/model_registry_and_verifier_policy.md`.

## Output Leakage

The circuit hides raw input features and the exact semantic-group SHAP values. It intentionally reveals `y_hat` and the top-3 semantic group IDs because these are the certified IDS decision and explanation summary. The resulting privacy claim is input-feature privacy, not complete behavioral secrecy. See `reports/stage34_output_leakage_audit.md` for a distributional audit of these public outputs.

## Input Provenance and Audit Binding

Stage 3.4 proves that the public prediction and top-3 semantic explanation are consistent with the same private witness. It does not, by itself, prove that the witness came from a specific external log row or previously registered event. A deployment that needs this stronger audit guarantee can add an input commitment at ingestion time and require the proof to open that public commitment inside the circuit. This is useful for provenance and cross-proof consistency, but it is separate from the input-feature privacy provided by the private witness and is outside the implemented Stage 3.4 claim.

## Reference Sensitivity

The implemented Stage 3.4 circuit fixes the training-mean reference vector. Alternative reference vectors are not additional ZK claims, but an offline sensitivity analysis is useful for critical self-assessment. See `reports/exact_shap_reference_sensitivity.md`.

## Critical Self-Assessment

Stage 3.4 strengthens the thesis contribution, but the scope boundaries remain explicit. The implementation is validated only in the IDS case study. Hidden-model support is outside the selected public-model/private-input threat model. Input commitments are optional future work for provenance or cross-proof consistency, not a requirement for input privacy. Exact SHAP verification is specialized to public Logistic Regression with fixed reference masking. Alternative reference vectors are sensitivity checks, not additional ZK claims. The system does not provide confidential-model support, arbitrary-model Exact SHAP, Partition SHAP, or sumcheck/GKR. The binary IDS task also remains constrained by the Logistic Regression accuracy trade-off relative to the stronger XGBoost plaintext baseline.

## Thesis-Ready Conclusion

The final Stage 3.4 result is not merely an additional circuit: it changes the verified explanation target from an engineering proxy to semantic-group Exact SHAP, while keeping proof generation practical through a mathematically justified closed form for linear models. This provides a clear research contribution and a defensible path for future work on larger models and scalable SHAP verification.
