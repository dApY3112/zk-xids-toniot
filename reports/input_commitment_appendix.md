# Appendix: Optional Input Commitment Prototype

The main ZK-XIDS prototype proves correct Logistic Regression prediction and semantic-group Exact SHAP top-3 explanation for a private witness, but Stage 3.4 deliberately does not bind that witness to a concrete log row. This appendix evaluates a small Stage 3.5 extension that adds such a binding point without changing the main claim.

The extension computes a public Poseidon rolling commitment over `(domain_tag, metadata_hash, salt, x_shifted[104])`. `metadata_hash` is public, `salt` and `x_shifted` are private, and the resulting `input_commitment` is a public signal. A verifier can then reject proofs whose public commitment does not match a commitment registered when the log row was ingested.

In this experiment the circuit grows from 8358 to 25094 constraints, about 3.0x the Stage 3.4 constraint count. The mean proving time over the tested samples is 2730.3 ms and the mean verification time is 1041.0 ms.

The negative test tampers with public signal 0, which is the commitment, and the Groth16 verifier rejects the proof. This supports the appendix claim that commitment binding is technically feasible, but it should not be described as a full provenance system unless an external trusted ingestion registry is also implemented.

Detailed generated evidence: `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md`.
