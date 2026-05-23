# Model Visibility Threat Model for ZK-XIDS

Generated: 2026-05-22

## Purpose

This note clarifies what is private in the current ZK-XIDS implementation and how a hidden-model variant could be added later without overstating the implemented result.

## Current Implemented Setting

The implemented Stage 3 pipeline uses a public-model, private-input setting.

| Item | Current status | Reason |
|---|---|---|
| Logistic Regression weights and bias | Public / fixed / auditable | The verifier can independently know which approved public model is being proved. |
| Processed network-flow input `x` | Private witness | Raw or processed traffic features are not revealed in public proof signals. |
| Prediction `y_hat` | Public output | The verifier learns the IDS decision being certified. |
| Stage 3.4 Exact SHAP top-3 IDs | Public output | The verifier learns the semantic explanation summary. |
| Exact SHAP values `phi_g` | Private intermediate | The circuit uses them for ranking but does not publish all group magnitudes. |
| Reference vector `x_ref` | Fixed by circuit artifact | Stage 3.4 hardcodes the training-mean reference vector in the circuit. |

The privacy claim is therefore input-feature privacy, not model confidentiality.

## How the Input Is Hidden

The prover supplies `x_shifted[104]` as private witness values to the Groth16 circuit. The circuit checks that these private values satisfy the public prediction and explanation claims, but the proof only exposes public signals such as the model parameters, `y_hat`, and top-3 group IDs. Under the zero-knowledge property of Groth16, the verifier learns that a valid private input exists and satisfies the relation, without seeing the feature vector itself.

This is the correct answer if asked: "the input is hidden as private witness data inside the SNARK; the verifier sees only the proof and the declared public outputs."

## Input Privacy vs Input Provenance

The current proof hides the processed feature vector during verification, but it does not by itself bind the hidden witness to a specific external record. A Stage 3.4 proof shows that there exists some private `x_shifted[104]` satisfying the approved model, prediction, and top-3 Exact SHAP relation. If an auditor also needs to know that this was the same input as a particular SIEM event, log row, or previously registered data record, the deployment needs an additional provenance mechanism.

One natural extension is an input commitment recorded at data ingestion time, for example `C_x = Hash(x_shifted, metadata, salt)`, with the circuit later checking that the private witness opens to the public commitment. This would provide audit binding or cross-proof consistency while keeping the feature values hidden. It is not required for input-feature privacy and is not implemented in the current Stage 3.4 circuit.

## Why Public Model Is Still a Defensible Thesis Scope

Public model does not mean weak privacy. It means the thesis studies a different threat model:

- auditable IDS deployment, where the SOC, regulator, or evaluator must know exactly which detector is being used;
- benchmarked academic evaluation, where reproducibility of the LR model is important;
- client-side or tenant-side proof, where the sensitive object is the network telemetry, not the model IP;
- verified explanation authenticity, where the contribution is proving that the prediction and semantic explanation come from the same private input.

This scope is narrower than confidential ML-as-a-service, but it is not empty. The implemented contribution is verified semantic explainability for IDS under private inputs, upgraded in Stage 3.4 from an engineering attribution proxy to semantic-group Exact SHAP.

The public-model/private-input setting is broader than IDS. IDS/SOC is a natural case study because auditability is intuitive: the verifier may need to know which detector is approved while the tenant or client keeps traffic features private. The same visibility logic applies to any approved public model with private tabular inputs, such as healthcare risk scores, credit-risk models, IoT monitoring models, or academic benchmark classifiers. Model binding by public artifact hash is sufficient only because the model is public; it verifies model identity but does not hide the model.

## What Hidden-Model Support Would Add

A hidden-model extension would protect model IP in addition to input privacy. It would change the public statement from "this known public model produced this result" to "some committed model produced this result."

One natural design is a committed-model relation:

```text
Public:
  C_model
  y_hat
  top3_ids
  model_version or policy metadata

Private:
  w[104]
  b
  x_ref[104]
  x[104]
  salt

Circuit:
  C_model = Poseidon(w, b, x_ref, salt)
  score = sum_i w_i * x_i + b
  y_hat = threshold(score)
  phi_g = sum_{i in G_g} w_i * (x_i - x_ref_i)
  top3_ids = TopK(abs(phi_g))
```

For Logistic Regression, semantic-group Exact SHAP still has the same closed form if the weights and reference vector are private but fixed by `C_model`. The extra cost comes from hashing and from proving model-parameter range checks privately. The verifier also needs a policy for accepting `C_model`, otherwise the prover could commit to an arbitrary weak model.

## Why Commitment Does Not Replace Input Privacy

A commitment is useful for binding a hidden model to a proof, but it does not make the input more private than the current SNARK already does. Input privacy already comes from private witness values and the zero-knowledge property. Model commitments solve a separate problem: model identity and model confidentiality.

## Model Binding vs Model Confidentiality

The current public-model setting still needs verifier-side model identity checking. A valid proof only says that the supplied public inputs satisfy the circuit relation; the verifier must also decide whether those public model inputs belong to the approved public model version.

When the model is public, checking a public artifact hash is enough for model binding. The verifier can compare the public weights, bias, feature order, semantic group map, bounds, Exact SHAP reference vector, circuit version, and verification key against an approved registry entry. The optional helper `tools/generate_model_registry.py` writes such a thesis-facing manifest to `stage3_zk/artifacts/model_registry_stage34.json`.

This does not provide model confidentiality. The model remains public and auditable. A committed hidden-model design would instead prove a relation such as `C_model = Poseidon(w, b, x_ref, salt)` with `w`, `b`, and `x_ref` kept private. That is future work and is not implemented in the current repository.

## Thesis Positioning

Recommended current claim:

> We implement SNARK verification of semantic-group Exact SHAP for an approved public Logistic Regression model under private input features. In this repository, the empirical instantiation is the TON_IoT intrusion detection case study.

Recommended future-work claim:

> A committed hidden-model variant could bind private LR weights, bias, and reference vector to a public model commitment, extending the same Exact SHAP relation to model-confidential deployments.

Do not claim that hidden-model support, confidential-model proofs, arbitrary-model Exact SHAP, sumcheck/GKR, or Partition SHAP are implemented in the current repository.
