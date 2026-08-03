# Stage 3.5 Appendix Artifact Audit

Scope: this audit covers only the optional Stage 3.5 Poseidon input-commitment prototype. No circuit, proof, setup, witness, or generated build artifacts were modified or regenerated for this audit.

## Single File To Include Or Excerpt

Recommended repository-relative path:

`stage3_zk/circuits/exact_shap_top3_commitment/exact_shap_top3_commitment.circom`

Recommendation: include selected excerpts, not the whole file.

Why this file should be selected:

- It is the actual Circom source defining the Stage 3.5 proof relation.
- It documents the public/private signal boundary, the public `input_commitment` output, the private `salt`, and the rolling Poseidon commitment over `x_shifted[104]`.
- It shows that Stage 3.5 extends the Stage 3.4 Logistic Regression plus semantic-group Exact SHAP top-3 relation instead of replacing it with a different computation.
- Reports and runner scripts document measurements and evidence generation, but they do not define the circuit relation itself.

The whole file is only 345 lines, so it can be included if the appendix allows full source listings. However, selected excerpts are preferable for a thesis appendix because they keep the appendix focused on the commitment prototype rather than repeating all Stage 3.4 logic.

## Relevant Templates, Functions, And Line Ranges

| File excerpt | Lines | Purpose | Include in appendix? |
|---|---:|---|---|
| `pragma` and includes | 1-4 | Shows Circom version and use of `comparators.circom` and `poseidon.circom`. | Optional |
| `template Select5()` | 6-35 | Helper for selecting one absolute SHAP value by 1-indexed semantic group ID. | Cite only unless ranking constraints are discussed |
| `template CheckGroupId()` | 37-49 | Enforces group IDs in the valid range 1-5. | Optional excerpt |
| `template RollingInputCommitment(n)` | 51-92 | Core Stage 3.5 addition: rolling Poseidon commitment over a domain tag, public `metadata_hash`, private `salt`, and private `x_shifted[n]`. | Yes |
| `template ExactShapTop3(...)` signal interface | 94-103 | Defines private inputs, public inputs, and public output `input_commitment`. | Yes |
| Hardcoded semantic group map | 105-112 | Shows the fixed five-group feature mapping reused by the explanation relation. | Cite only |
| Hardcoded Exact SHAP reference vector | 114-124 | Shows the circuit embeds the fixed reference vector generated from `exact_shap_reference.json`. | Cite only, or short excerpt if discussing reference input |
| Commitment wiring | 131-137 | Wires `x_shifted`, `metadata_hash`, and `salt` into `RollingInputCommitment` and exposes the result as `input_commitment`. | Yes |
| LR score and prediction constraints | 139-198 | Shows the Stage 3.4 public Logistic Regression prediction relation remains part of the Stage 3.5 circuit. | Cite only, or excerpt if appendix must be self-contained |
| Semantic-group Exact SHAP and absolute values | 200-249 | Shows private internal group SHAP values and absolute magnitudes used for ranking. | Cite only, or excerpt if appendix must be self-contained |
| Top-3 group validity, distinctness, dominance, and order | 251-340 | Shows public top-3 IDs are checked against the remaining private group IDs and ordered by non-increasing absolute SHAP value. | Cite only, or excerpt if appendix must be self-contained |
| Public/private `main` declaration | 342-345 | Confirms public inputs are `w_shifted`, `b_shifted`, `metadata_hash`, `y_hat`, and `top3_ids`; `input_commitment` is a public output. | Yes |

Suggested minimal appendix excerpt set:

- Lines 51-92: `RollingInputCommitment(n)`.
- Lines 94-103: Stage 3.5 signal interface.
- Lines 131-137: commitment wiring.
- Lines 342-345: public/private `main` declaration.

Suggested extended excerpt set if the appendix should be self-contained:

- Add lines 139-198 for Logistic Regression prediction constraints.
- Add lines 200-249 for semantic-group Exact SHAP and absolute values.
- Add lines 251-340 for top-3 ranking validity, distinctness, dominance, and ordering.

## Supporting Files To Cite But Not Reproduce

These files support the appendix claim but should normally be cited rather than reproduced:

- `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md`
  - Generated Stage 3.5 measurement report.
  - Contains the reported circuit delta, artifact sizes, proof results, timing summary, and interpretation.
- `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.json`
  - Machine-readable source for the reported Stage 3.5 numbers.
  - Contains `circuit_stats`, `artifact_sizes`, sample proof timings, public signal counts, and tampered-commitment test results.
- `reports/input_commitment_appendix.md`
  - Narrative appendix summary generated from the Stage 3.5 evidence.
  - Useful for wording, but less authoritative than the circuit source.
- `stage3_zk/scripts/stage 3.5/00_compile_circuit_stage35.ps1`
  - Lines 13-23 show the circuit path and WSL Circom compile command.
- `stage3_zk/scripts/stage 3.5/01_prepare_input_stage35.py`
  - Lines 2-12 describe the prototype scope.
  - Lines 47-49 compute a field hash from simulated metadata text.
  - Lines 68-111 prepare Stage 3.5 input JSON by adding public `metadata_hash` and private `salt`.
- `stage3_zk/scripts/stage 3.5/02_run_stage35_commitment.py`
  - Lines 85-109 parse R1CS circuit statistics.
  - Lines 172-190 implement the tampered public commitment negative test.
  - Lines 193-245 generate witness, proof, verification, and public signal evidence.
  - Lines 291-394 write the generated report and narrative appendix file.
- `stage3_zk/reports/STAGE34_PROOF_REPORT.md`
  - Baseline Stage 3.4 evidence for comparison.
- `stage3_zk/reports/STAGE34_PROOF_REPORT.json`
  - Machine-readable Stage 3.4 baseline metrics used by the Stage 3.5 report.
- `stage3_zk/artifacts/model_public.json`
  - Public quantized model values used by the circuit input generation.
- `stage3_zk/artifacts/group_map.json`
  - Semantic group mapping used to generate the hardcoded circuit map.
- `stage3_zk/artifacts/exact_shap_reference.json`
  - Source artifact for the fixed Exact SHAP reference vector embedded in the circuit.
- `stage3_zk/artifacts/bounds.json`
  - Quantization and range-bound source artifact.
- `stage3_zk/artifacts/model_registry_stage34.json`
  - Stage 3.4 registry and verifier policy context; useful for explaining why Stage 3.5 remains appendix-only.
- `stage3_zk/test_vectors/test_sample_1.json`, `stage3_zk/test_vectors/test_sample_7.json`, and `stage3_zk/test_vectors/test_sample_8.json`
  - Test-vector context for the three Stage 3.5 proof runs.

## Generated Artifacts That Must Not Be Included

Do not reproduce generated binary or build artifacts in the thesis appendix:

- `stage3_zk/circuits/exact_shap_top3_commitment/build/exact_shap_top3_commitment.r1cs`
- `stage3_zk/circuits/exact_shap_top3_commitment/build/exact_shap_top3_commitment_0000.zkey`
- `stage3_zk/circuits/exact_shap_top3_commitment/build/exact_shap_top3_commitment_final.zkey`
- `stage3_zk/circuits/exact_shap_top3_commitment/build/exact_shap_top3_commitment_js/exact_shap_top3_commitment.wasm`
- `stage3_zk/circuits/exact_shap_top3_commitment/build/witness_sample_1.wtns`
- `stage3_zk/circuits/exact_shap_top3_commitment/build/witness_sample_7.wtns`
- `stage3_zk/circuits/exact_shap_top3_commitment/build/witness_sample_8.wtns`

Also avoid reproducing generated or witness-derived auxiliary files unless a short excerpt is explicitly needed:

- `stage3_zk/circuits/exact_shap_top3_commitment/build/exact_shap_top3_commitment.sym`
- `stage3_zk/circuits/exact_shap_top3_commitment/build/exact_shap_top3_commitment_js/generate_witness.js`
- `stage3_zk/circuits/exact_shap_top3_commitment/build/exact_shap_top3_commitment_js/witness_calculator.js`
- `stage3_zk/circuits/exact_shap_top3_commitment/build/verification_key.json`
- `stage3_zk/circuits/exact_shap_top3_commitment/build/input_sample_1.json`
- `stage3_zk/circuits/exact_shap_top3_commitment/build/input_sample_7.json`
- `stage3_zk/circuits/exact_shap_top3_commitment/build/input_sample_8.json`
- `stage3_zk/outputs/commitments/sample_1_metadata.json`
- `stage3_zk/outputs/commitments/sample_7_metadata.json`
- `stage3_zk/outputs/commitments/sample_8_metadata.json`
- `stage3_zk/outputs/proofs/stage35/proof_stage35_sample_1.json`
- `stage3_zk/outputs/proofs/stage35/proof_stage35_sample_7.json`
- `stage3_zk/outputs/proofs/stage35/proof_stage35_sample_8.json`
- `stage3_zk/outputs/proofs/stage35/public_stage35_sample_1.json`
- `stage3_zk/outputs/proofs/stage35/public_stage35_sample_7.json`
- `stage3_zk/outputs/proofs/stage35/public_stage35_sample_8.json`
- `stage3_zk/outputs/proofs/stage35/public_stage35_sample_1_tampered_commitment.json`
- `stage3_zk/outputs/proofs/stage35/public_stage35_sample_7_tampered_commitment.json`
- `stage3_zk/outputs/proofs/stage35/public_stage35_sample_8_tampered_commitment.json`

These generated files can be cited as reproducibility artifacts, but the appendix should not print them as source evidence.

## Match To Reported Stage 3.5 Values

The selected `.circom` file directly matches the reported Stage 3.5 public/private interface:

- Public inputs from the `main` declaration:
  - `w_shifted[104]`
  - `b_shifted`
  - `metadata_hash`
  - `y_hat`
  - `top3_ids[3]`
  - Total: 104 + 1 + 1 + 1 + 3 = 110 public inputs.
- Private inputs from the circuit template:
  - `x_shifted[104]`
  - `salt`
  - `other2_ids[2]`
  - Total: 104 + 1 + 2 = 107 private inputs.
- Public output:
  - `input_commitment`
  - This explains why proof files contain 111 public signals: 110 public inputs plus 1 public output.

The numeric circuit and timing values are not embedded in the source file itself. They are generated evidence from `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.json` and `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md`. The reported values match the selected circuit as the compiled Stage 3.5 relation:

| Reported value | Status | Evidence |
|---|---|---|
| 25,094 constraints | Matches generated report | `circuit_stats.constraints = 25094` |
| 24,816 wires | Matches generated report | `circuit_stats.wires = 24816` |
| 110 public inputs | Matches circuit interface and generated report | `main` public list plus `circuit_stats.public_inputs = 110` |
| 107 private inputs | Matches circuit interface and generated report | private template inputs plus `circuit_stats.private_inputs = 107` |
| 586 ms mean witness time | Matches after rounding | report mean `585.7 ms`, rounded to `586 ms` |
| 2,730 ms mean proving time | Matches after rounding | report mean `2730.3 ms`, rounded to `2730 ms` |
| 1,041 ms mean verification time | Matches report | report mean `1041.0 ms` |

Additional consistency note: the report records successful proofs for samples 1, 7, and 8 and negative tests where tampering with public signal 0, the public `input_commitment`, is rejected.

## Proposed Appendix Title

`Appendix X: Stage 3.5 Poseidon Input-Commitment Prototype`

## Thesis-Safe Description

Stage 3.5 is an optional appendix prototype that extends the Stage 3.4 proof relation with a public Poseidon rolling commitment over `(domain_tag, metadata_hash, salt, x_shifted[104])`. The private witness still contains the processed input vector, and the added private `salt` is used in the commitment. The public signals include the existing public Logistic Regression prediction and ordered top-3 semantic group identifiers, plus public `metadata_hash` and the public output `input_commitment`.

The prototype shows that the same private input witness used for prediction and semantic-group Exact SHAP ranking can also be constrained to open to a public commitment. This provides a technical binding point that could be checked against an external ingestion-time commitment registry.

This appendix must not claim full provenance, SIEM ingestion authenticity, replay protection, or production readiness. The circuit does not prove that the metadata came from an authentic log source, does not maintain a trusted registry, does not enforce freshness or anti-replay policy, and does not make the system deployment-ready. Those properties would require additional external system design beyond the implemented Stage 3.5 circuit.
