# Method Choice: Semantic-Group Exact SHAP for ZK-XIDS

Generated: 2026-05-22T14:46:43+00:00 (UTC)

## Why keep the grouped linear attribution baseline

The existing attribution `sum_i |w_i*x_i|` per semantic group is engineering-heavy in a useful way: it is simple, deterministic, cheap to compute, easy to quantize, and already maps cleanly to the current Circom/Groth16 Stage 3.2 and Stage 3.3 circuits. That makes it a good proof-of-concept baseline for verifiable explanation authenticity.

Its academic limitation is that it is not a Shapley-value explanation. It depends on the feature origin and uses absolute linear terms rather than marginal contributions under a coalition game.

## Why semantic-group Exact SHAP is stronger

Exact SHAP treats the five semantic groups as players and assigns each group the weighted average of its marginal effect over every coalition. The value function is the Logistic Regression score or logit, and removed groups are replaced by the feature-wise training-set mean in processed feature space. This gives a thesis-ready explanation method with a clear cooperative-game definition.

The method is feasible here because there are only five players. Exact enumeration requires only 2^5 coalition states per sample, so there is no need to approximate with Monte Carlo SHAP or Partition SHAP in the current scope.

## ZK positioning

The current system setting is public-model, private-input: the Logistic Regression weights and bias are public, while the processed network traffic features remain private witness values. The Stage 3 SNARK stack is Circom + Groth16 only.

Stage 3.4 verifies semantic-group Exact SHAP top-3 authenticity for the public Logistic Regression model. This works because the Exact SHAP coalition definition collapses exactly to a group-wise closed form for a linear score model with fixed reference masking. Sumcheck/GKR is future scalability work and is not implemented or tested in this repo. Partition SHAP is also future work for larger or hierarchical group sets.

## Algorithm: Semantic-Group Exact SHAP for ZK-XIDS

Inputs: public model `F`, private input `x`, semantic groups `G`, reference vector `x_ref`

Outputs: `y_hat`, `phi_g(x)`, top-k groups, proof `pi`

```text
1. Compute y_hat = F(x).
2. For each semantic group g in G:
   a. Enumerate all coalitions S subseteq G \ {g}.
   b. For each S, form masked inputs where groups outside S are set to x_ref.
   c. Compute the marginal score contribution F(x_{S union g}) - F(x_S).
   d. Weight the marginal by |S|! (m-|S|-1)! / m!.
3. Sum weighted marginals to obtain phi_g(x) for every group.
4. Select the top-k semantic groups by explanation magnitude.
5. Stage 3.4 proves prediction and top-k Exact SHAP groups are tied to the same private input x.
6. The circuit keeps phi_g(x) private and publishes only y_hat plus top-k group IDs.
```

This circuit is model-specific to Logistic Regression. No model-agnostic verifier, sumcheck protocol, GKR verifier, Partition SHAP implementation, confidential-model proof, arbitrary-model Exact SHAP circuit, or differential privacy mechanism has been implemented or tested. Input-provenance binding is not part of Stage 3.4; it is only explored in the optional Stage 3.5 input-commitment appendix prototype.
