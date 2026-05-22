# Semantic-Group Exact SHAP Results

Generated: 2026-05-22T14:46:43+00:00 (UTC)

## Scope

This evaluation computes semantic-group Exact SHAP for the public Logistic Regression model and compares it with the older grouped linear attribution proxy. The same closed-form Exact SHAP relation is now verified by the Stage 3.4 Circom/Groth16 circuit for the fixed public LR model under private input features.

For group `g`, with `m=5` semantic groups, the script computes:

```text
phi_g(x) = sum_{S subseteq G \ {g}} |S|! (m-|S|-1)! / m! * (v_x(S union {g}) - v_x(S))
```

Here `v_x(S)` is the Logistic Regression score/logit after keeping groups in `S` from `x` and replacing all removed groups with `x_ref`.

## Configuration

- Model: Logistic Regression (`C:\Paper\Masters thesis\outputs\models\logreg_baseline.pkl`)
- Value function: model score/logit, not probability
- Reference vector: feature-wise training-set mean in processed feature space
- Quantized reference artifact: `stage3_zk/artifacts/exact_shap_reference.json`
- Subset: `reconstructed_stage2_lr_tp1000_fn100_seed42` (1100 samples)
- Output CSV: `outputs/explainability/exact_shap_semantic_groups.csv`
- SHAP players: five semantic groups
- Exact SHAP top-3 ranking: descending absolute SHAP value, preserving signed SHAP columns
- Engineering baseline: grouped `sum_i |w_i * x_i|`, matching the current Stage 2/3 attribution family

## Group Summary

| Group | Size | Mean abs Exact SHAP | Mean old grouped attribution | Exact top-3 count | Old top-3 count |
|---|---:|---:|---:|---:|---:|
| Protocol | 3 | 1.151115 | 3.059726 | 1044 | 1094 |
| Application | 76 | 0.733157 | 9.164932 | 415 | 1100 |
| ConnectionState | 13 | 1.607628 | 1.641246 | 1061 | 547 |
| Ports | 2 | 0.258602 | 0.286670 | 250 | 80 |
| TrafficVolume | 10 | 0.468695 | 0.904034 | 530 | 479 |

## Agreement Between Methods

- Mean top-3 overlap count: `2.0618` out of 3
- Mean top-3 Jaccard overlap: `0.5407`
- Max enumeration-vs-closed-form SHAP difference: `2.842171e-14`
- Max SHAP additivity residual: `2.842171e-14`
- Max score reconstruction difference: `1.421085e-14`

## Closed-Form Equivalence for Logistic Regression

For a linear score model and fixed reference masking, the marginal contribution of group `g` does not depend on the coalition `S`. Therefore the exact Shapley sum collapses to:

```text
phi_g(x) = sum_{i in G_g} w_i * (x_i - x_ref_i)
```

The script verifies this by comparing coalition enumeration over the five groups with the closed-form group score difference. This closed form is the Stage 3.4 circuit target.

For integer ZK arithmetic, the reference artifact stores:

- `Sx = 65536` and `Sw = 4096`
- `max_abs_x_ref_int = 65527`
- conservative `max_abs_phi_int` bound = `82150463534784`
- `phi_g_int = sum_i w_int[i] * (x_int[i] - x_ref_int[i])`

## Interpretation

The old grouped linear attribution is useful for engineering because it is cheap, deterministic, easy to quantize, and already has a compact SNARK relation in Stage 3.2/3.3. Its limitation is that `abs(w_i*x_i)` measures contribution magnitude relative to zero, not marginal contribution relative to a well-defined background input.

Semantic-group Exact SHAP is academically stronger because each group receives a Shapley value computed from all coalitions of present/removed semantic groups. Removed groups are replaced by the training-set mean, so the explanation is tied to an explicit reference distribution and the LR score decomposition satisfies the SHAP efficiency property.

Because there are only five semantic groups, exact enumeration is feasible: each sample evaluates all coalitions over five players, avoiding sampling variance and avoiding Partition SHAP heuristics in the current implementation.

## ZK Status

Stage 3 remains SNARK-only. Stages 3.1-3.3 prove Logistic Regression inference and the older grouped linear attribution proxy. Stage 3.4 verifies the semantic-group Exact SHAP top-3 relation for the public Logistic Regression model by using the closed-form LR specialization above. This is not confidential-model support, not arbitrary-model SHAP verification, and not sumcheck/GKR or Partition SHAP.
