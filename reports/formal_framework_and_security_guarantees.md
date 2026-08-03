# Formal Framework and Security Guarantees

Generated: 2026-05-24

## Purpose

This report states the formal core of the implemented thesis contribution. The implementation is a public-model/private-input zero-knowledge proof pattern for verifiable semantic explanations, instantiated in the ZK-XIDS intrusion detection case study.

The formal claim is intentionally scoped:

> Given an approved public Logistic Regression model, a fixed feature order, a fixed semantic group map, and a fixed reference vector, Stage 3.4 proves in Groth16 that the public prediction and a valid ordered non-increasing top-3 semantic-group Exact SHAP explanation are computed from the same private input feature vector.

This report does not claim model-agnostic verification, hidden-model support, confidential-model proofs, arbitrary-model Exact SHAP, Partition SHAP, sumcheck/GKR, differential privacy, or XGBoost-in-ZK. The main Stage 3.4 formal claim also excludes input provenance binding; the optional Stage 3.5 appendix prototype evaluates a commitment-based binding point separately.

## System Model

### Parties

- Prover: holds a private processed tabular input vector `x`.
- Verifier: checks a Groth16 proof and interprets the public prediction and explanation.
- Model registry: records the approved public model version and associated artifacts.

### Public Artifacts

The verifier policy fixes the following public artifacts:

- Logistic Regression weights `w` and bias `b`.
- Feature order for the processed vector.
- Semantic group map `G = {G_1, ..., G_m}`.
- Input bounds and quantization configuration.
- Reference vector `x_ref`.
- Stage 3.4 circuit version and verification key.
- Artifact registry digest identifying the approved public model version.

In the implemented case study, `m = 5`, the feature count is `d = 104`, and the semantic groups are Protocol, Application, ConnectionState, Ports, and TrafficVolume.

### Private Witness

The private witness contains:

- shifted/encoded private input features `x_shifted[104]`;
- helper values needed by the circuit, such as remaining group identifiers for the top-3 ranking check.

The raw or processed input feature values are not public signals.

### Public Outputs

The verifier intentionally learns:

- prediction `y_hat`;
- ordered non-increasing top-3 semantic group identifiers `top3_ids`.

The circuit does not publish processed input feature values or all semantic-group Exact SHAP values. The privacy claim is therefore input-feature privacy with intentional output disclosure.

### Statement, Witness, and Leakage

The public statement for Stage 3.4 is:

```text
stmt = (model_id, w_shifted, b_shifted, y_hat, top3_ids, vk_id)
```

where `model_id` abbreviates the approved registry entry containing the feature order, group map, bounds, reference vector, circuit version, and verification key identity. In the concrete Circom public input list, the public model is represented by `w_shifted[104]` and `b_shifted`, while the verifier-side registry policy binds these values to the approved model version.

The private witness is:

```text
wit = (x_shifted[104], other2_ids[2], auxiliary witness values)
```

where `other2_ids` are the remaining semantic groups used to verify that the public top-3 groups dominate the two non-public top-3 candidates.

The intended leakage function is:

```text
L(wit) = (approved public model/version metadata, y_hat, top3_ids)
```

plus public proof-system metadata such as proof size, verification key identity, and the fact that verification accepted. No raw feature value and no full vector of semantic-group SHAP magnitudes is part of the intended leakage.

## Semantic-Group Exact SHAP Definition

Let the semantic groups be the players:

```text
G = {G_1, ..., G_m}
```

For a coalition `S subseteq G`, define a masked input `x^S`:

```text
x^S_i = x_i      if the semantic group containing feature i is in S
x^S_i = x_ref_i  otherwise
```

The value function is the Logistic Regression score/logit:

```text
v_x(S) = F(x^S) = b + sum_i w_i * x^S_i
```

The semantic-group Exact SHAP value for group `G_g` is:

```text
phi_g(x) =
  sum_{S subseteq G \ {G_g}}
    [ |S|! * (m-|S|-1)! / m! ] *
    ( v_x(S union {G_g}) - v_x(S) )
```

The implemented explanation publishes only the ordered non-increasing top-3 group identifiers by `abs(phi_g)`. If two groups have equal absolute value, more than one ordering may satisfy the circuit relation.

## Closed-Form Exact SHAP for Linear Score Models

### Theorem 1: Closed-Form Semantic-Group Exact SHAP

For a linear score model

```text
F(x) = b + sum_i w_i * x_i
```

with fixed reference masking, the semantic-group Exact SHAP value for group `G_g` is:

```text
phi_g(x) = sum_{i in G_g} w_i * (x_i - x_ref_i)
```

### Proof Sketch

For any coalition `S` that does not contain group `G_g`, adding `G_g` changes only the features inside that group. Since `F` is linear:

```text
v_x(S union {G_g}) - v_x(S)
  = sum_{i in G_g} w_i * (x_i - x_ref_i)
```

This marginal contribution is independent of `S`. The Shapley weights over all coalitions excluding `G_g` sum to 1:

```text
sum_{S subseteq G \ {G_g}} |S|! * (m-|S|-1)! / m! = 1
```

Therefore the weighted sum equals the same constant marginal contribution:

```text
phi_g(x) = sum_{i in G_g} w_i * (x_i - x_ref_i)
```

This is why Stage 3.4 can verify Exact SHAP for the public Logistic Regression model without enumerating all coalitions inside the circuit.

## Stage 3.4 Relation

Let `pub` denote the public inputs and registered artifacts, and let `wit` denote the private witness. The Stage 3.4 relation is:

```text
R_Stage34(pub; wit) = 1
```

if and only if all of the following hold:

1. The private encoded input `x_shifted` is in the permitted range.
2. The circuit recovers the signed integer input vector `x_int` according to the approved encoding convention.
3. The approved public Logistic Regression score is computed correctly:

   ```text
   s_int = b_int + sum_i w_int[i] * x_int[i]
   ```

4. The public prediction `y_hat` matches the approved threshold rule for `s_int`.
5. For each semantic group `G_g`, the circuit computes the closed-form integer Exact SHAP score:

   ```text
   phi_g_int = sum_{i in G_g} w_int[i] * (x_int[i] - x_ref_int[i])
   ```

6. The circuit computes `abs(phi_g_int)` for all groups.
7. The public `top3_ids` are valid group identifiers.
8. The top-3 group identifiers are distinct.
9. The helper remaining group identifiers complete a valid permutation of all semantic groups.
10. The ordered non-increasing top-3 condition holds:

    ```text
    abs(phi_top1) >= abs(phi_top2) >= abs(phi_top3)
    abs(phi_top3) >= abs(phi_remaining1)
    abs(phi_top3) >= abs(phi_remaining2)
    ```

11. The public model artifacts are interpreted only under the approved verifier-side registry policy.

The relation binds the prediction and explanation to the same private input because the same recovered `x_int` is used in both the score computation and the Exact SHAP computation.

### Tie-Breaking Semantics

The implemented circuit verifies dominance and non-increasing order using `>=` comparisons over `abs(phi_g_int)`. Therefore, if two semantic groups have exactly equal absolute Exact SHAP magnitude, the circuit accepts any ordering that satisfies the non-increasing constraints and the permutation constraints.

The Stage 3.4 input generator uses a deterministic convention when constructing witnesses: sort by descending absolute magnitude and then by smaller group identifier. This makes generated artifacts reproducible, but the current circuit does not enforce that secondary group-ID tie-break rule cryptographically.

The safest formal statement is therefore:

> The proof certifies that the public `top3_ids` form a valid ordered non-increasing top-3 ranking by absolute semantic-group Exact SHAP value. Ties may admit multiple valid certified rankings.

If a deployment requires a unique canonical ranking, the circuit should be extended with lexicographic tie-breaking constraints, for example: when `abs(phi_a) = abs(phi_b)`, the lower group identifier must appear first. That extension is not implemented in the current Stage 3.4 circuit.

## Protocol Construction

### Setup and Registration

1. Fix the approved public Logistic Regression model, feature order, semantic group map, bounds, quantization configuration, reference vector, circuit version, and verification key.
2. Compute artifact hashes and a combined registry digest.
3. Register the approved public model version and artifact digest.

This step provides model-version binding for the public-model setting. It does not provide model confidentiality.

### Prove

Input:

- approved public artifacts;
- private processed input `x`;
- requested public outputs `y_hat` and `top3_ids`.

Steps:

1. Encode and range-check the private input.
2. Compute the Logistic Regression score and prediction.
3. Compute closed-form semantic-group Exact SHAP values.
4. Select a valid ordered non-increasing top-3 group list by absolute value. The implementation's witness generator uses smaller group identifier as an off-circuit deterministic tie-break for reproducibility.
5. Generate a Groth16 proof for `R_Stage34`.

Output:

- proof `pi`;
- public prediction `y_hat`;
- public ordered non-increasing top-3 semantic group identifiers.

### Verify

The verifier accepts only if:

1. The verification key corresponds to the approved Stage 3.4 circuit version.
2. The public model artifacts match the approved registry entry.
3. The artifact digest identifies the approved public model version.
4. The Groth16 proof verifies for the public signals.
5. The public `y_hat` and `top3_ids` are interpreted as the certified prediction and semantic explanation.

## Security Guarantees

### Theorem 2: Soundness of Verified Prediction and Explanation

Assuming Groth16 knowledge soundness for the compiled Stage 3.4 circuit, if the verifier accepts a proof for public outputs `(y_hat, top3_ids)` and approved public artifacts, then except with negligible probability there exists a private witness `x_shifted` such that:

- `x_shifted` satisfies the input range and encoding constraints;
- `y_hat` is the correct Logistic Regression prediction for that private input;
- `top3_ids` are a valid ordered non-increasing top-3 semantic group list by absolute closed-form Exact SHAP value;
- the prediction and explanation are computed from the same private input.

This guarantee is computational and inherits the assumptions and setup requirements of Groth16.

### Theorem 3: Input-Feature Privacy up to Intentional Output Disclosure

Assuming the zero-knowledge property of Groth16, the verifier learns no private witness values beyond what is revealed by the public statement and the intended leakage function `L`.

In the implemented Stage 3.4 setting, the public statement includes:

- approved public model artifacts and verification policy metadata;
- prediction `y_hat`;
- ordered non-increasing top-3 semantic group identifiers.

Therefore, the proof hides the private input feature vector and the full Exact SHAP score vector, but it does not hide the intentionally disclosed outputs. The system provides input-feature privacy, not complete behavioral secrecy.

This is a zero-knowledge privacy statement, not a differential-privacy statement. The current system does not add calibrated noise to `y_hat` or `top3_ids`, and therefore it should not claim differential privacy. The entropy and frequency analyses in the repository are empirical output-leakage audits; they help describe what the disclosed outputs look like on the evaluation subset, but they are not cryptographic privacy proofs and not mutual-information bounds over all possible input distributions.

### Ranking Stability Boundary

The circuit verifies correctness of a ranking for a given private input. It does not prove that the ranking is stable under perturbations of that input. Ranking stability is a separate robustness property: when two groups have close absolute SHAP magnitudes, a small change in `x` can change the top-3 order or membership.

For the public Logistic Regression setting, each semantic-group Exact SHAP value is linear in the input:

```text
phi_g(x) = sum_{i in G_g} w_i * (x_i - x_ref_i)
```

Thus the perturbation sensitivity of each group can be bounded by the group weight norm. For example, under an infinity-norm input perturbation `||delta||_infty <= epsilon`:

```text
|phi_g(x + delta) - phi_g(x)| <= epsilon * sum_{i in G_g} |w_i|
```

A sufficient margin condition for preserving a top-3 separation is that the gap between the third-ranked group and every non-top-3 group is larger than the corresponding perturbation bound. This margin analysis is not implemented as a circuit claim; it is an optional robustness analysis for discussion and future work.

### Input Provenance Boundary

The Stage 3.4 proof certifies consistency with some private witness. It does not by itself prove that the witness came from a specific external log row or previously registered event.

The optional Stage 3.5 appendix prototype implements one binding point by checking a public Poseidon commitment to `(domain_tag, metadata_hash, salt, x_shifted[104])` inside the circuit. This demonstrates feasibility, but a full provenance guarantee still requires an external trusted registry that stores the same commitment at ingestion time. This is an auditability extension, not a prerequisite for input privacy.

## Complexity Analysis

Generic semantic-group Exact SHAP over `m` groups requires coalition enumeration:

```text
O(m * 2^m)
```

For `m = 5`, this is already feasible outside the circuit and was used as the Python reference implementation. However, Stage 3.4 uses the closed-form theorem for public Logistic Regression:

```text
O(d)
```

where `d` is the number of processed features.

The implemented case study has:

| Quantity | Value |
|---|---:|
| Processed features `d` | 104 |
| Semantic groups `m` | 5 |
| Published explanation size `k` | 3 |
| Stage 3.4 constraints | 8358 |
| Stage 3.4 wires | 8078 |
| Stage 3.4 public inputs | 109 |
| Stage 3.4 private inputs | 106 |

The Stage 3.4 circuit is smaller than the earlier Stage 3.3 grouped-attribution top-3 circuit in the current artifact set:

| Stage | Explanation target | Constraints | Wires |
|---|---|---:|---:|
| 3.3 | Old grouped linear attribution proxy top-3 | 18719 | 18043 |
| 3.4 | Semantic-group Exact SHAP top-3 | 8358 | 8078 |

The lower Stage 3.4 constraint count is a consequence of verifying the linear closed-form Exact SHAP relation rather than the older absolute feature-contribution aggregation proxy.

## Empirical Validation Obligations

The current repository supports the formal claim with the following evidence:

- Python coalition enumeration equals the closed-form LR Exact SHAP values up to numerical precision.
- Stage 3.4 witness generation, proof generation, and verification pass on selected test samples.
- Negative tests reject malformed predictions, malformed top-3 explanations, duplicate group identifiers, out-of-range group identifiers, malicious remaining identifiers, and private input range violations.
- Proof cost and artifact sizes are reported for Stage 3.4.
- Output leakage is audited for the public `y_hat` and top-3 semantic group identifiers.
- Reference sensitivity is evaluated offline as a robustness and self-assessment check.
- Model-version binding is handled by a verifier-side registry policy for the approved public model.
- Optional input-commitment evidence is reported separately as an appendix Stage 3.5 prototype; it is not part of the main Stage 3.4 theorem.

## Minimum Security-Oriented Treatment

For a security-oriented workshop or thesis defense, the minimal formal treatment should include:

1. A precise public statement and private witness definition.
2. A verifier-side model-binding policy that prevents arbitrary prover-selected public model parameters.
3. A formal relation `R_Stage34(pub; wit)` covering prediction, Exact SHAP group computation, permutation checks, and non-increasing top-3 dominance.
4. A theorem reducing correctness to Groth16 knowledge soundness for the compiled circuit.
5. A theorem reducing private-input confidentiality to Groth16 zero-knowledge with an explicit leakage function.
6. A clear tie semantics statement: the implemented circuit certifies a valid non-increasing ranking, not a unique canonical ranking under ties.
7. A statement that output leakage is intentional and not differential privacy.
8. A complexity statement comparing generic group Exact SHAP enumeration `O(m * 2^m)` with the Logistic Regression closed form `O(d)`.
9. Empirical evidence that the Python Exact SHAP reference, witness generation, proof generation, verification, and negative tests match the formal relation.

This is sufficient for positioning the work as a concrete applied zkML/XAI system contribution. It is not sufficient to claim a new cryptographic primitive, a confidential-model protocol, or a general SHAP verification protocol for arbitrary models.

## Scope Boundaries

The following are deliberate scope boundaries, not implemented claims:

- Public-model/private-input only.
- Logistic Regression or compatible public linear/logistic tabular models only.
- Fixed semantic group map.
- Fixed reference vector.
- Exact SHAP verification specialized to the linear-score closed form.
- Top-3 semantic group identifiers are intentionally public.
- Processed input feature values and full Exact SHAP scores remain private.
- Model confidentiality is not implemented.
- Hidden-model commitments are not implemented.
- Input commitment is not part of the main Stage 3.4 claim; an optional Stage 3.5 appendix prototype demonstrates a Poseidon commitment check for provenance or cross-proof consistency.
- Sumcheck/GKR is not implemented.
- Partition SHAP is not implemented.
- XGBoost-in-ZK is not implemented.

## Research Positioning

The strongest current contribution is a concrete SNARK relation and implementation for verifying semantic-group Exact SHAP top-3 explanations under private inputs for an approved public Logistic Regression model.

The contribution is best described as an applied cryptography and trustworthy AI systems contribution. It is not a new proof system and does not introduce cryptographic novelty at the level of a new SNARK, commitment scheme, or sumcheck protocol.

The proof-pattern claim is valid only under the stated scope: public linear/logistic tabular models, fixed semantic groups, fixed reference masking, and intentional disclosure of prediction and top-3 semantic explanation identifiers.
