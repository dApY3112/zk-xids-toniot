# Model Registry and Verifier Policy for Stage 3.4

Generated: 2026-05-22

## Purpose

This report clarifies the model-version binding story for the implemented public-model, private-input Stage 3.4 design. The current IDS instantiation verifies semantic-group Exact SHAP top-3 explanations for an approved public Logistic Regression model. It does not implement hidden-model commitments or confidential-model proofs.

## Input Privacy Does Not Require an Input Commitment

The processed network-flow vector `x_shifted[104]` is supplied to the Groth16 circuit as private witness data. The verifier sees the proof and public signals, but not the private witness. Under the zero-knowledge property, the verifier learns that some private input satisfies the verified relation without learning the raw feature values.

Therefore, an input commitment is not required for input privacy in the current design. A commitment to the input may be useful in future deployments for other reasons, such as:

- cross-proof consistency, where several proofs must refer to the same hidden input;
- provenance, where a later audit needs to bind a proof to an external logged event;
- delayed disclosure, where the prover may later reveal the input and prove it matches the original proof context.

Those are useful system features, but they are not prerequisites for the current privacy claim.

## Public Model Binding

Because the Logistic Regression model is public, model binding can be handled outside the circuit by verifier policy. The verifier should not accept an arbitrary public weight vector merely because a proof verifies. The verifier must also check that the public model artifacts match an approved public model version.

In the current public-model setting, this can be done by hashing and registering the approved artifacts:

- `stage3_zk/artifacts/model_public.json`
- `stage3_zk/artifacts/feature_order.json`
- `stage3_zk/artifacts/group_map.json`
- `stage3_zk/artifacts/bounds.json`
- `stage3_zk/artifacts/exact_shap_reference.json`
- `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`
- `stage3_zk/circuits/exact_shap_top3/build/verification_key.json`

This is model binding, not model confidentiality. The verifier knows the model and checks its identity.

Verifier-side model-version binding is not IDS-specific. It is required whenever a proof must be interpreted with respect to an approved public model version rather than arbitrary prover-selected public parameters. Similar logic applies to healthcare tabular models, credit-risk models, IoT monitoring models, and academic benchmark models.

## Verifier Acceptance Algorithm

The verifier accepts a Stage 3.4 proof only if:

1. The verification key corresponds to the approved Stage 3.4 circuit version.
2. The public weights and bias match the approved `model_public.json`.
3. The feature order, semantic group map, quantization configuration, and Exact SHAP reference vector match the approved artifacts.
4. The approved artifact digest or model identifier matches the registered model version.
5. The Groth16 proof verifies.
6. The public `y_hat` and `top3_ids` are interpreted as the certified prediction and semantic explanation.

This policy closes the public-model identity gap without adding hidden-model machinery to the circuit.

The optional checker command is:

```powershell
python tools/verify_stage34_policy.py --self-test
```

## Difference from Hidden-Model Commitment

Hidden-model support would require a different proof relation. A typical future design would publish a model commitment while keeping the model parameters private:

```text
Public:
  C_model
  y_hat
  top3_ids

Private:
  w
  b
  x_ref
  x
  salt

Circuit:
  C_model = Poseidon(w, b, x_ref, salt)
  y_hat = F_w,b(x)
  phi_g = sum_{i in G_g} w_i * (x_i - x_ref_i)
  top3_ids = TopK(abs(phi_g))
```

That design would bind a private model to a public commitment. It is future work and is not implemented in the current repository.

## Implemented vs Future Work

| Capability | Status |
|---|---|
| Private input inference | Implemented |
| Verified top-3 semantic explanation | Implemented |
| Verified semantic-group Exact SHAP | Implemented in Stage 3.4 |
| Public model registry / model-version binding | Thesis-level verifier policy |
| Input commitment | Optional future work |
| Hidden model commitment | Future work |
| Sumcheck/GKR | Future work |
| Partition SHAP | Future work |
| XGBoost-in-ZK | Future work |

## Recommended Thesis Claim

The thesis should claim public-model, private-input verification:

> The verifier checks a registered approved public Logistic Regression model and a Stage 3.4 Groth16 proof showing that the public prediction and top-3 semantic Exact SHAP explanation were computed from the same private input. In this repository, the approved model is the IDS Logistic Regression artifact for the TON_IoT case study.

It should not claim confidential-model support, hidden-model commitments, sumcheck/GKR, Partition SHAP, or XGBoost-in-ZK.
