# Appendix A Evidence Package: Reproducibility and Stage 3.4 Implementation

This file is a repository-grounded evidence package for preparing Appendix A of the thesis. It records the current Stage 3.4 implementation, reproduction path, proof evidence, and known audit gaps. It is not a polished thesis appendix and does not extend the claims supported by the implementation.

## A.1 Repository and Experiment Identification

| Item | Verified value | Evidence source |
|---|---|---|
| Thesis working title | *A Zero-Knowledge Framework for Verifiable Semantic Explanations: An Intrusion Detection Case Study* | Audit specification |
| Repository project title | *A Scoped Zero-Knowledge Framework for Verifiable Semantic Explanations under Private Inputs: An Intrusion Detection Case Study* | `README.md` |
| Git commit | `586b51bd0e21d2a59da5270b39e307adcc743a0a` | `git rev-parse HEAD`, audited 2026-06-15 |
| Git branch | `main` | `git branch --show-current`, audited 2026-06-15 |
| Evidence-package generation time | `2026-06-15T15:44:04Z` | Audit timestamp |
| Dataset | Processed TON_IoT network data, 23 CSV files | `reports/dataset_summary.md`; `outputs/splits/data_manifest.json` |
| Dataset file pattern | `data/processed/Processed_Network_dataset/Network_dataset_*.csv` | `outputs/splits/data_manifest.json` |
| Dataset mode | `processed_stratified_sample_23files_frac0.15` | `reports/dataset_summary.md`; `outputs/splits/split_meta.json` |
| Sampling | 15% independently sampled from each of 23 processed files | `reports/dataset_summary.md` |
| Split | Stratified train/validation/test = 70/15/15 | `reports/dataset_summary.md`; `outputs/splits/split_meta.json` |
| Random seed | `42` | `outputs/splits/split_meta.json` |
| Row counts | Total 3,350,853; train 2,345,597; validation 502,628; test 502,628 | `reports/dataset_summary.md`; `outputs/splits/split_meta.json` |
| Processed feature count | 104 | `stage3_zk/artifacts/feature_order.json`; circuit main component |
| Semantic groups | 5: Protocol, Application, ConnectionState, Ports, TrafficVolume | `stage3_zk/artifacts/group_map.json` |
| Public proof-compatible model | Logistic Regression | `README.md`; `stage3_zk/artifacts/model_public.json` |
| Stronger plaintext baseline | XGBoost | `README.md`; `reports/baseline_extended_metrics.md` |
| Proof stage | Stage 3.4 | `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |
| Proof system | Circom/Groth16 on `bn-128` | `stage3_zk/scripts/stage 3.4/04_run_phase_c_stage34.py`; current `snarkjs r1cs info` output |
| Main implemented relation | Stage 3.4 Exact SHAP top-3 verification: correct public quantized Logistic Regression prediction and valid ordered public top-3 semantic-group identifiers computed from a private processed input vector | `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom` |
| Visibility boundary | Public model parameters and explanation identifiers; private input features, remaining group identifiers, score, and SHAP values | Circuit public declaration and signal inventory in A.5 |
| Approved Stage 3.4 digest | `6c3c9e086aceb1f2a0038c1c3726baf49998a310fcd64421b98cadaf39e32b14` | `stage3_zk/artifacts/model_registry_stage34.json` |

## A.2 Software, Runtime, and Hardware Environment

The active audit environment, repository-pinned environment, and historical training environment are distinguished because they are not identical.

| Component | Version or configuration | Evidence source |
|---|---|---|
| Host operating system | Windows 11 Home Single Language, 64-bit, version `10.0.26200` | PowerShell system query, 2026-06-15 |
| CPU | 11th Gen Intel Core i5-11320H @ 3.20 GHz; 8 logical processors | PowerShell CIM query, 2026-06-15 |
| RAM | 7.79 GiB | PowerShell CIM query, 2026-06-15 |
| WSL | WSL `2.7.8.0`; kernel `6.18.33.1-1`; Ubuntu 22.04 WSL2 | `wsl --version`; WSL distribution query |
| Linux distribution | Ubuntu `22.04.5 LTS` | `/etc/os-release` under WSL |
| Circom compiler used for Stage 3.4 | `2.2.3` under WSL; source pragma `2.1.9` | `circom -V`; circuit line 1; compile script |
| Node.js / npm | Node `v20.12.2`; npm `10.8.3` | `node --version`; `npm --version` |
| SnarkJS / circomlib | SnarkJS `0.7.5`; circomlib `2.0.5` | `stage3_zk/package-lock.json`; repository SnarkJS CLI |
| Historical/unused npm `circom` package | `0.5.46`; not the Circom 2 compiler used by the Stage 3.4 compile script | `stage3_zk/package-lock.json`; compile script |
| Active audit Python | Python `3.12.3`; NumPy `1.26.4`; pandas `2.3.3`; scikit-learn `1.5.1`; XGBoost `3.0.5`; joblib `1.4.2`; matplotlib `3.9.2` | Runtime package queries, 2026-06-15 |
| Pinned ML environment | NumPy `1.26.4`; pandas `2.3.3`; scikit-learn `1.4.2`; XGBoost `3.1.2`; joblib `1.4.2`; matplotlib `3.9.2` | `requirements-ml.lock.txt` |
| Historical baseline environment | Conda environment `py310` / Python 3.10; exact patch version not pinned | `README.md` |

GPU information is omitted because no GPU is required or reported for the Stage 3.4 Groth16 workflow.

## A.3 Minimal Reproduction Workflow

Commands are repository-relative. No single documented environment bootstrap or end-to-end data-to-proof command exists; notebook execution and environment preparation require manual sequencing.

| Step | Repository-relative command | Inputs | Expected outputs | Evidence source |
|---:|---|---|---|---|
| 1 | No canonical install command located. Prepare the Python environment from `requirements-ml.lock.txt` and Node dependencies from `stage3_zk/package-lock.json`. | Lock files and WSL Circom 2.2.3 | Python/Node/Circom environment | Lock files; A.13 G2 |
| 2 | `python tools/reproduce.py check` | Existing dataset/model/artifact paths | Prerequisite presence/status output | `README.md`; `tools/reproduce.py` |
| 3 | Manually run `notebooks/01_data_sanity_check.ipynb`, `notebooks/02_train_val_test_split.ipynb`, and `notebooks/03_preprocessing_pipeline.ipynb` in order. | Processed TON_IoT CSV files | Processed features and split metadata | `README.md`; notebook paths |
| 4 | `conda run -n py310 python tools/train_baselines.py` | Prepared train/validation/test data | Logistic Regression and XGBoost model artifacts | `README.md` |
| 5 | `conda run -n py310 python tools/reproduce.py all-eval --ratios "0.25,0.5,1,2,5,10,20,50,100"` | Models and split data | Deterministic evaluation reports in A.4 | `README.md`; `tools/reproduce.py` |
| 6 | Manually run `notebooks/05b_stage2_semantic_grouping.ipynb` and `notebooks/06_stage3_prepare_artifacts.ipynb`. | Public Logistic Regression model and processed features | Initial semantic-group and ZK model artifacts | `README.md`; notebook paths |
| 7 | `python tools/reproduce.py semantic-groups` | Exported LR artifacts, group map, and reference data | Exact SHAP semantic-group report/artifacts | `README.md`; `reports/README.md`; `tools/reproduce.py` |
| 8 | `python tools/reproduce.py stage34-vectors` | Current Stage 3.4 artifacts and selected test records | `stage3_zk/test_vectors/test_sample_1.json` through `test_sample_8.json` | `README.md`; `reports/README.md` |
| 9 | `powershell -ExecutionPolicy Bypass -File "stage3_zk/scripts/stage 3.4/02_compile_circuit_stage34.ps1"` | Circuit source, circomlib, and WSL Circom 2 | R1CS, WASM, and symbol artifacts | `stage3_zk/scripts/stage 3.4/02_compile_circuit_stage34.ps1` |
| 10 | `python tools/reproduce.py zk-stage34 --samples 1,2,3,4,5,6,7,8 --force-setup` | R1CS, Powers of Tau, and test vectors | Prototype-local Groth16 setup, one local contribution, vkey, and the complete sample run | `tools/reproduce.py`; Stage 3.4 runner lines 98-145 |
| 11 | `node stage3_zk/circuits/exact_shap_top3/build/exact_shap_top3_js/generate_witness.js stage3_zk/circuits/exact_shap_top3/build/exact_shap_top3_js/exact_shap_top3.wasm stage3_zk/circuits/exact_shap_top3/build/input_sample_1.json stage3_zk/circuits/exact_shap_top3/build/witness_sample_1.wtns` | Sample-1 circuit input and WASM | Sample-1 witness | Stage 3.4 runner lines 148-164; repeat with sample IDs 2-8 |
| 12 | `node stage3_zk/node_modules/snarkjs/cli.js groth16 prove stage3_zk/circuits/exact_shap_top3/build/exact_shap_top3_final.zkey stage3_zk/circuits/exact_shap_top3/build/witness_sample_1.wtns stage3_zk/outputs/proofs/proof_stage34_sample_1.json stage3_zk/outputs/proofs/public_stage34_sample_1.json` | Final zkey and sample-1 witness | Sample-1 proof and public signals | Stage 3.4 runner lines 166-173; repeat with sample IDs 2-8 |
| 13 | `node stage3_zk/node_modules/snarkjs/cli.js groth16 verify stage3_zk/circuits/exact_shap_top3/build/verification_key.json stage3_zk/outputs/proofs/public_stage34_sample_1.json stage3_zk/outputs/proofs/proof_stage34_sample_1.json` | Vkey, public signals, and proof | Groth16 verification result | Stage 3.4 runner lines 175-180; repeat with sample IDs 2-8 |
| 14 | `python tools/reproduce.py stage34-batch-smoke --samples 30 --prove 30 --seed 34030` | Processed test split and existing Stage 3.4 setup | Supplemental 30-sample witness/prove/verify smoke-test report | `stage3_zk/scripts/stage 3.4/05_batch_smoke_stage34.py`; `stage3_zk/reports/STAGE34_BATCH_SMOKE_REPORT.md` |
| 15 | `cd stage3_zk` then `npm run test:stage34:negative` | Current WASM and samples 1-8 | Six expected witness-generation rejections per sample | `stage3_zk/package.json`; negative-test script |
| 16 | `python tools/generate_model_registry.py` | Approved public artifacts, circuit source, and vkey | Registry JSON and combined digest | `stage3_zk/README.md`; registry generator |
| 17 | `python tools/verify_stage34_policy.py` | Registry, approved digest, proof, public signals, vkey | Normal local policy and Groth16 verification | Policy verifier |
| 18 | `python tools/verify_stage34_policy.py --self-test` | Same artifacts plus in-memory mutations | Positive acceptance and expected policy rejections | `README.md`; `stage3_zk/README.md`; policy verifier |
| 19 | `python tools/generate_stage34_thesis_reports.py` then `python tools/reproduce.py source-truth` | Current machine-readable reports | Thesis-facing Stage 3.4 reports and final source map | `reports/README.md`; `README.md` |

The setup step calls SnarkJS `groth16 setup`, performs one local contribution with fresh runtime entropy, and exports a verification key. This is adequate for the reported proof-of-concept experiment but is not evidence of a production multiparty trusted setup.

Audit note: the current compile script internally contains a machine-specific WSL path. The repository-relative wrapper above is valid only on a checkout that matches that internal path unless the script is made path-independent.

## A.4 Authoritative Artifact and Result Map

| Result or artifact category | Authoritative source | Purpose | Thesis use | Status |
|---|---|---|---|---|
| Final number precedence | `reports/final_numbers_source_of_truth.md` | Resolves overlapping reports | First reference for final values | authoritative |
| Baseline ML metrics | `reports/baseline_extended_metrics.md` | Imbalance-aware LR/XGBoost metrics | Chapter 7 baseline table | authoritative |
| Operating points and calibration | `reports/decision_engineering_baselines.md` | Thresholds, confusion counts, calibration | Operating-point analysis | authoritative |
| Cost-sensitive thresholds | `reports/cost_based_thresholds.md` | Validation-selected FN/FP trade-offs | Cost analysis | authoritative |
| File-wise holdout | `reports/filewise_holdout.md` | Cross-file robustness | Generalization/limitation evidence | authoritative |
| Attack-type analysis | `reports/attack_type_error_analysis.md` | Errors by attack family | Post-hoc error analysis | authoritative |
| Float-versus-quantized LR agreement | `reports/float_vs_quantized_lr_agreement.md` | ML-to-ZK relation agreement | Quantization validity | authoritative |
| Exact SHAP ranking margin | `reports/exact_shap_ranking_margin.md` | Rank-3/rank-4 stability evidence | Explanation limitation analysis | authoritative |
| Stage 3.1-3.3 evidence | `stage3_zk/reports/LATEST_REPRO_REPORT.md` | Earlier staged proof evidence | Historical implementation context | authoritative |
| Stage 3.4 proof evidence | `stage3_zk/reports/STAGE34_PROOF_REPORT.md` | Current eight-sample proof size/timing/PASS data | Final Stage 3.4 evidence | authoritative |
| Stage 3.4 diverse test vectors | `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md` | Selection rationale for samples 4-8 | Functional coverage manifest | supporting |
| Stage 3.4 batch smoke test | `stage3_zk/reports/STAGE34_BATCH_SMOKE_REPORT.md` | Deterministic label-balanced 30-sample witness/prove/verify smoke test | Supporting functional evidence only | supporting |
| Verifier policy and registry | `reports/model_registry_and_verifier_policy.md`; `stage3_zk/artifacts/model_registry_stage34.json` | Artifact binding and approved digest | Verifier-boundary evidence | authoritative |
| Quantization and ranking ECDF figures | `THESIS_ECDF_GENERATION_REPORT.md`; `reports/figures/thesis_extra/` | Distribution figures and generation record | Supporting figures | supporting |
| Stage 3.5 report | `stage3_zk/reports/STAGE35_INPUT_COMMITMENT_REPORT.md` | Optional input-commitment feasibility prototype | Outside the main Stage 3.4 claim | appendix-only |

### Historical artifacts that must not be used for final Stage 3.4 claims

Historical or non-authoritative artifacts must not replace the sources above:

- `stage3_zk/reports/bench/` contains older benchmark material.
- `stage3_zk/outputs/proofs/` contains raw proof/public artifacts and older Node-API timing material; it is not the final Stage 3.4 timing source.
- `stage3_zk/reports/STAGE34_EXACT_SHAP_SUMMARY.md` is a status and negative-test summary, not the authoritative eight-sample timing report.
- `stage3_zk/reports/zk_stage34_scaling_benchmark.md` is supporting repeated-sample benchmarking and does not replace `stage3_zk/reports/STAGE34_PROOF_REPORT.md`.

## A.5 Stage 3.4 Public, Private, Constant, and Internal Values

The compiled R1CS reports 109 public inputs, 106 private inputs, and zero Circom output signals. `y_hat` and `top3_ids` are public result values in thesis terminology, but technically they are constrained public input signals.

| Signal or artifact category | Visibility | Count | Defined in | Role |
|---|---|---:|---|---|
| `w_shifted` | Circom public signal | 104 | Circuit lines 52 and 287-290 | Encoded public Logistic Regression weights |
| `b_shifted` | Circom public signal | 1 | Circuit lines 53 and 287-290 | Encoded public Logistic Regression bias |
| `y_hat` | Circom public signal | 1 | Circuit lines 54, 84, and 141-143 | Public binary prediction constrained to equal the score sign |
| `top3_ids` | Circom public signal | 3 | Circuit lines 55, 196-201, and 287-290 | Ordered public semantic-group IDs |
| Public-input total | Circom public signals | 109 | Current R1CS information | `104 + 1 + 1 + 3` |
| `x_shifted` | Private witness | 104 | Circuit lines 51, 86-93, and 111-114 | Encoded private processed features |
| `other2_ids` | Private witness | 2 | Circuit lines 56 and 204-214 | Remaining semantic-group IDs used to verify global top-3 membership |
| Private-input total | Private witness | 106 | Current R1CS information | `104 + 2` |
| `score`, `pred`, partial sums | Internal computed signals | 1 score, 1 prediction, 105 partial sums | Circuit lines 119-143 | Logistic Regression score and prediction derivation |
| `Phi`, `absPhi` | Internal computed signals | 5 signed and 5 absolute values | Circuit lines 145-194 | Semantic-group Exact SHAP values used for ranking; not disclosed |
| Ranking helper signals | Internal computed signals | Five mapped magnitudes plus comparators | Circuit lines 245-284 | Selection, dominance, and non-increasing-order constraints |
| Circom outputs | No `signal output` declaration | 0 | Current R1CS information | Public results are public inputs, not output signals |
| `group_id` | Embedded circuit constant | 104 entries | Circuit lines 58-65 | Compile-time feature-to-group map |
| `x_ref_int` | Embedded circuit constant | 104 entries | Circuit lines 67-77 | Quantized training-mean Exact SHAP reference |
| Bounds `B`, `maxAbsX`, `maxAbsW`, `BPhi` | Embedded circuit constants/parameters | 4 | Circuit lines 79-82 and 287-290 | Signed encodings and comparator ranges |
| Quantization scales `Sx`, `Sw` | Export-artifact constants; not circuit signals | 2 | `stage3_zk/artifacts/model_public.json`; `stage3_zk/artifacts/exact_shap_reference.json` | Convert floating model/input values to integer artifacts before proof generation |
| Circuit version | Source/compiler metadata | 1 | Circuit pragma line 1; compile environment | Source requires Circom 2.1.9 syntax and is compiled with Circom 2.2.3 |
| Verification key | Checked only by verifier policy/Groth16 verifier | 1 artifact | Registry and circuit build directory | Selects the approved Groth16 verification relation |
| Registry digest | Checked only by verifier policy | 1 value | `model_registry_stage34.json`; policy verifier | Binds the locally approved public artifact set |

The proof does not hide the public model, prediction, or selected group identifiers. It hides the processed input, internal score, all five SHAP values, and the identities of the two remaining groups.

## A.6 Selected Stage 3.4 Circuit Excerpts

### Excerpt: Main template and signal declarations

Source: `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`, lines 50-56  
Component: `ExactShapTop3`

```circom
template ExactShapTop3(n, nBits, B, maxAbsX, maxAbsW, nGroups) {
    signal input x_shifted[n];      // Private: x_int[i] + maxAbsX
    signal input w_shifted[n];      // Public: w_int[i] + maxAbsW
    signal input b_shifted;         // Public: b_int + B
    signal input y_hat;             // Public prediction
    signal input top3_ids[3];       // Public top-3 semantic groups by abs(Exact SHAP)
    signal input other2_ids[2];     // Private remaining group IDs
```

Explanation: The template declares the candidate public and private values. The visibility boundary becomes effective through the `main` public list shown below; the interface contains no public commitment to a source log row or SIEM event.

### Excerpt: Semantic-group ID validity

Source: `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`, lines 36-48  
Component: `CheckGroupId`

```circom
template CheckGroupId() {
    signal input id;

    component notZero = IsEqual();
    notZero.in[0] <== id;
    notZero.in[1] <== 0;
    notZero.out === 0;

    component inRange = LessThan(3);
    inRange.in[0] <== id;
    inRange.in[1] <== 6;
    inRange.out === 1;
}
```

Explanation: Each group ID must be nonzero and less than 6, hence one of `1, 2, 3, 4, 5`.

### Excerpt: Shifted-input range checks and signed recovery

Source: `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`, lines 86-93 and 106-117  
Component: `ExactShapTop3`

```circom
component xRangeCheck[n];

for (var i = 0; i < n; i++) {
    xRangeCheck[i] = LessThan(30);
    xRangeCheck[i].in[0] <== x_shifted[i];
    xRangeCheck[i].in[1] <== 2 * maxAbsX + 1;
    xRangeCheck[i].out === 1;
}
```

```circom
signal x[n];
signal w[n];
signal b;
signal c[n];

for (var i = 0; i < n; i++) {
    x[i] <== x_shifted[i] - maxAbsX;
    w[i] <== w_shifted[i] - maxAbsW;
    c[i] <== w[i] * x[i];
}

b <== b_shifted - B;
```

Explanation: `x_shifted` is range-constrained as a non-negative field encoding, and the signed feature is recovered as `x_shifted[i] - maxAbsX`. The same offset pattern is used for public weights and the intercept.

### Excerpt: Logistic Regression score accumulation

Source: `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`, lines 119-127  
Component: `ExactShapTop3`

```circom
signal partialSum[n + 1];
partialSum[0] <== 0;

for (var i = 0; i < n; i++) {
    partialSum[i + 1] <== partialSum[i] + c[i];
}

signal score;
score <== partialSum[n] + b;
```

Explanation: The integer score is `sum_i(w_int[i] * x_int[i]) + b_int`, using the same recovered private input and public weights later used by Exact SHAP.

### Excerpt: Prediction threshold and public consistency

Source: `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`, lines 129-143  
Component: `ExactShapTop3`

```circom
signal score_offset;
score_offset <== score + B;

component scoreBoundCheck = LessThan(38);
scoreBoundCheck.in[0] <== score_offset;
scoreBoundCheck.in[1] <== 2 * B;
scoreBoundCheck.out === 1;

component scoreSignCheck = LessThan(nBits);
scoreSignCheck.in[0] <== score_offset;
scoreSignCheck.in[1] <== B;

signal pred;
pred <== 1 - scoreSignCheck.out;
pred === y_hat;
```

Explanation: With `score_offset = score + B`, the prediction is 1 when `score >= 0`. The public `y_hat` must be binary and equal this internally derived prediction.

### Excerpt: Semantic-group Exact SHAP computation

Source: `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`, lines 145-167  
Component: `ExactShapTop3`

```circom
// Closed-form semantic-group Exact SHAP for LR score:
// phi_g_int = sum_{i in group g} w_int[i] * (x_int[i] - x_ref_int[i]).
signal phi_term[n];
signal phi_acc[nGroups][n + 1];
signal Phi[nGroups];
signal absPhi[nGroups];
signal phi_offset[nGroups];
signal phi_sign[nGroups];

for (var g = 0; g < nGroups; g++) {
    phi_acc[g][0] <== 0;
}

for (var i = 0; i < n; i++) {
    phi_term[i] <== w[i] * (x[i] - x_ref_int[i]);
    for (var g = 0; g < nGroups; g++) {
        if (group_id[i] == g + 1) {
            phi_acc[g][i + 1] <== phi_acc[g][i] + phi_term[i];
        } else {
            phi_acc[g][i + 1] <== phi_acc[g][i];
        }
    }
}
```

Explanation: The same recovered private input and public weights used for prediction are used for group attribution. `Phi` and `absPhi` are internal signals and are not public outputs.

### Excerpt: Signed SHAP encoding and absolute value

Source: `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`, lines 169-194  
Component: `ExactShapTop3`

```circom
component phiBoundCheck[nGroups];
component phiSignCheck[nGroups];
component absPhiBoundCheck[nGroups];

for (var g = 0; g < nGroups; g++) {
    Phi[g] <== phi_acc[g][n];
    phi_offset[g] <== Phi[g] + BPhi;

    phiBoundCheck[g] = LessThan(nBitsPhi);
    phiBoundCheck[g].in[0] <== phi_offset[g];
    phiBoundCheck[g].in[1] <== 2 * BPhi;
    phiBoundCheck[g].out === 1;

    phiSignCheck[g] = LessThan(nBitsPhi);
    phiSignCheck[g].in[0] <== phi_offset[g];
    phiSignCheck[g].in[1] <== BPhi;
    phi_sign[g] <== phiSignCheck[g].out;
    phi_sign[g] * (phi_sign[g] - 1) === 0;

    absPhi[g] <== (1 - 2 * phi_sign[g]) * Phi[g];

    absPhiBoundCheck[g] = LessThan(nBitsPhi);
    absPhiBoundCheck[g].in[0] <== absPhi[g];
    absPhiBoundCheck[g].in[1] <== BPhi;
    absPhiBoundCheck[g].out === 1;
}
```

Explanation: The sign bit is derived from the bounded offset representation. If `Phi < 0`, `phi_sign = 1` and the expression returns `-Phi`; otherwise it returns `Phi`.

### Excerpt: Group-ID distinctness across selected and remaining groups

Source: `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`, lines 209-227  
Component: `ExactShapTop3`

```circom
signal all_ids[5];
all_ids[0] <== top3_ids[0];
all_ids[1] <== top3_ids[1];
all_ids[2] <== top3_ids[2];
all_ids[3] <== other2_ids[0];
all_ids[4] <== other2_ids[1];

component neq[10];
var k = 0;

for (var i = 0; i < 5; i++) {
    for (var j = i + 1; j < 5; j++) {
        neq[k] = IsEqual();
        neq[k].in[0] <== all_ids[i];
        neq[k].in[1] <== all_ids[j];
        neq[k].out === 0;
        k++;
    }
}
```

Explanation: Pairwise inequality covers all ten pairs across the three public and two private IDs. Together with the separate range checks, the five IDs form a permutation of 1-5; lines 229-243 also enforce the expected sum and squared sum.

### Excerpt: Top-3 dominance over both remaining groups

Source: `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`, lines 245-274  
Component: `ExactShapTop3`

```circom
signal mappedAbsPhi[5];
component sel[5];

for (var idx = 0; idx < 5; idx++) {
    sel[idx] = Select5();
    sel[idx].arr <== absPhi;
    sel[idx].idx <== all_ids[idx];
    mappedAbsPhi[idx] <== sel[idx].out;
}

component dominance[6];
var dom_idx = 0;

for (var t = 0; t < 3; t++) {
    for (var o = 3; o < 5; o++) {
        dominance[dom_idx] = LessThan(nBitsPhi);
        dominance[dom_idx].in[0] <== mappedAbsPhi[t];
        dominance[dom_idx].in[1] <== mappedAbsPhi[o];
        dominance[dom_idx].out === 0;
        dom_idx++;
    }
}
```

Explanation: Each selected public top-3 group, including the third-ranked group, must have an absolute value greater than or equal to each privately identified remaining group.

### Excerpt: Non-increasing public top-3 order

Source: `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`, lines 276-284  
Component: `ExactShapTop3`

```circom
component order01 = LessThan(nBitsPhi);
order01.in[0] <== mappedAbsPhi[0];
order01.in[1] <== mappedAbsPhi[1];
order01.out === 0;

component order12 = LessThan(nBitsPhi);
order12.in[0] <== mappedAbsPhi[1];
order12.in[1] <== mappedAbsPhi[2];
order12.out === 0;
```

Explanation: This enforces non-increasing magnitude. It does not enforce a deterministic group-ID tie-break; smaller-ID tie-breaking is performed only by the off-circuit input preparation code.

### Excerpt: Main component public declaration

Source: `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`, lines 287-290  
Component: `main`

```circom
// Public: w_shifted[104], b_shifted, y_hat, top3_ids[3]
// Private: x_shifted[104], other2_ids[2]
component main {public [w_shifted, b_shifted, y_hat, top3_ids]} =
    ExactShapTop3(104, 37, 68719476736, 297270816, 122130, 5);
```

Explanation: This declaration makes the model parameters, prediction, and top-3 IDs public, while all undeclared template inputs remain private. It explains the compiled 109 public and 106 private input counts.

### Excerpt: Fixed reference and SHAP bound

Source: `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom`, lines 67-69 and 79-82  
Component: `ExactShapTop3`

The 104-element reference array between these excerpts is intentionally not reproduced.

```circom
// x_ref_int = round(training_mean_processed * Sx), generated in
// stage3_zk/artifacts/exact_shap_reference.json.
var x_ref_int[104] = [
```

```circom
// Conservative bound from exact_shap_reference.json:
// max_abs_phi_int <= 82150463534784 < 2^47.
var BPhi = 140737488355328; // 2^47
var nBitsPhi = 49;
```

Explanation: The reference is neither a witness nor a public signal. It is generated from the training processed-feature mean, quantized by `Sx`, and embedded as a circuit constant.

## A.7 Quantization, Bounds, and Finite-Field Safety Evidence

| Quantity | Verified bound or scale | Evidence source | Role |
|---|---|---|---|
| Input quantization | `x_int = round(x_float * 65,536)` | Export artifacts and input preparation | Fixed-point input scale `Sx = 2^16` |
| Weight quantization | `w_int = round(w_float * 4,096)` | `stage3_zk/artifacts/model_public.json` and export logic | Fixed-point weight scale `Sw = 2^12` |
| Intercept quantization | Encoded consistently with the integer dot-product score | `stage3_zk/artifacts/model_public.json`; Stage 3.4 input preparation | Public `b_int` is shifted by `B` for field input |
| Private input encoding | `x_shifted = x_int + maxAbsX` | Range check `0 <= x_shifted < 2*maxAbsX+1`; signed recovery in circuit | Represents `-maxAbsX <= x_int <= maxAbsX` |
| Public weight encoding | `w_shifted = w_int + maxAbsW` | Equivalent range check and recovery | Represents `-maxAbsW <= w_int <= maxAbsW` |
| Public intercept encoding | `b_shifted = b_int + B` | `0 <= b_shifted < 2*B+1` | Represents `-B <= b_int <= B` |
| Maximum configured input magnitude | `297,270,816` | Circuit parameter and `stage3_zk/artifacts/bounds.json` | Current enforced input bound |
| Maximum configured weight magnitude | `122,130` | Circuit parameter and `stage3_zk/artifacts/bounds.json` | Current enforced weight bound |
| Maximum individual LR product | `122,130 * 297,270,816 = 36,305,684,758,080` | Audit calculation from enforced bounds | Approximately 46 bits |
| Conservative 104-term score magnitude before circuit score check | `104 * maxAbsW * maxAbsX + B = 3,775,859,934,317,056` | Audit calculation | Approximately 52 bits; the circuit separately enforces the tighter `B` score range |
| Enforced score interval | `-B <= score < B`, where `B = 68,719,476,736` | `score_offset` range check | Prediction sign comparison is valid within this interval |
| Reference maximum magnitude | `65,527` | `stage3_zk/artifacts/exact_shap_reference.json` | Included in SHAP bound generation |
| Maximum individual SHAP term from simple global maxima | `maxAbsW * (maxAbsX + maxAbsRef) = 36,313,687,570,590` | Audit calculation | Approximately 46 bits |
| Conservative group SHAP bound from artifact generator | `82,150,463,534,784 < 2^47` | `stage3_zk/artifacts/exact_shap_reference.json`; circuit comment | Group-specific summation bound used to choose `BPhi` |
| Enforced SHAP interval | `-BPhi <= Phi < BPhi`, `BPhi = 2^47` | `phi_offset` and absolute-value checks | Prevents ambiguous signed interpretation within the configured range |
| Comparator bit width for SHAP | 49 bits | Circuit `nBitsPhi = 49` | Covers values below `2*BPhi = 2^48` |
| Current R1CS curve | `bn-128` | Current SnarkJS R1CS information | The configured values are far below the field modulus |

Finite-field safety is supported by explicit range constraints and by the small configured magnitudes: the largest simple audit bound above is approximately 52 bits, whereas the repository describes the target field as approximately 254 bits. This is strong implementation evidence against wraparound under the configured bounds, but the repository does not contain a separate formal Stage 3.4 overflow proof.

One artifact inconsistency must be preserved as an audit gap: `stage3_zk/artifacts/bounds.json` reports `max_abs_score_int = 22,988,183,559`, while the current circuit enforces `B = 68,719,476,736`, and selected valid samples include score magnitudes above the JSON value. The circuit bound and current proof report therefore govern Stage 3.4 execution; the JSON score field should be corrected or explicitly relabeled before final archival.

## A.8 Stage 3.4 Circuit and Proof Summary

| Metric | Current value | Evidence source |
|---|---:|---|
| R1CS constraints | 8,358 | `stage3_zk/reports/STAGE34_PROOF_REPORT.md`; current `snarkjs r1cs info` |
| R1CS wires | 8,078 | Same |
| Public inputs | 109 | Same |
| Private inputs | 106 | Same |
| Circom outputs | 0 | Current `snarkjs r1cs info` |
| R1CS size | 1,283,048 bytes | Stage 3.4 proof report and current file metadata |
| WASM size | 99,582 bytes | Same |
| Final zkey size | 4,573,072 bytes | Same |
| Verification-key size | 22,669 bytes | Same |
| Witness time, samples 1-8 | 58-72 ms; mean 62.75 ms, thesis-rounded to 63 ms | `stage3_zk/reports/STAGE34_PROOF_REPORT.md`; source-of-truth report |
| Proving time, samples 1-8 | 1,009-1,365 ms; mean 1,143.875 ms, thesis-rounded to 1,144 ms | Same |
| Verification time, samples 1-8 | 618-915 ms; mean 700.625 ms, thesis-rounded to 701 ms | Same |
| Proof JSON size | 800-807 bytes; final reported mean 804 bytes (raw arithmetic mean 804.5) | `stage3_zk/reports/STAGE34_PROOF_REPORT.md`; source-of-truth report |
| Public JSON size | 1,178 bytes for every sample | `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |
| Successful proof cases | 8 of 8 selected functional vectors | `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |

These eight vectors demonstrate functional coverage, not an estimate of proof reliability over a random population. A proof can correctly verify a model decision even when that decision is a false positive or false negative relative to the dataset label.

These measurements are local command-line prototype timings over the selected Stage 3.4 test vectors. They are not hardware-independent guarantees or production deployment benchmarks.

Supplemental batch smoke evidence is stored separately in `stage3_zk/reports/STAGE34_BATCH_SMOKE_REPORT.md`. That run selected 30 deterministic label-balanced test rows with seed 34030 and obtained 30/30 witness passes, 30/30 proof passes, 30/30 verification passes, and 30/30 public-output matches. It is supporting functional evidence only and does not replace the authoritative eight-vector proof-cost table above.

## A.9 Stage 3.4 Test-Vector Manifest

Semantic-group names are reported instead of numeric IDs for readability. The circuit uses IDs 1-5 and discloses only the ordered top three.

| Sample | Case label | Ground truth | Public prediction | Ordered public top-3 groups | Selection purpose | Witness | Proof | Verification | Evidence source |
|---:|---|---:|---:|---|---|---|---|---|---|
| 1 | True-positive attack | 1 | 1 | Application, ConnectionState, Protocol | Standard correctly detected attack | PASS | PASS | PASS | `reports/stage34_case_studies.md`; `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |
| 2 | True-negative normal | 0 | 0 | ConnectionState, Protocol, TrafficVolume | Standard correctly classified normal case | PASS | PASS | PASS | `reports/stage34_case_studies.md`; `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |
| 3 | False-negative attack | 1 | 0 | Protocol, Application, ConnectionState | Demonstrates proof correctness does not imply classifier correctness | PASS | PASS | PASS | `reports/stage34_case_studies.md`; `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |
| 4 | False-positive normal | 0 | 1 | TrafficVolume, Protocol, ConnectionState | Adds the missing classification-error quadrant | PASS | PASS | PASS | `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md`; `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |
| 5 | High-confidence attack | 1 | 1 | TrafficVolume, ConnectionState, Protocol | Exercises a large positive score | PASS | PASS | PASS | `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md`; `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |
| 6 | High-confidence normal | 0 | 0 | TrafficVolume, ConnectionState, Application | Exercises a large negative score near the configured circuit range | PASS | PASS | PASS | `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md`; `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |
| 7 | Borderline score | 1 | 0 | Application, TrafficVolume, ConnectionState | Exercises a decision close to the zero threshold | PASS | PASS | PASS | `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md`; `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |
| 8 | Small top-3 margin | 1 | 1 | ConnectionState, Protocol, Ports | Exercises explanation ranking with a small rank-3/rank-4 gap | PASS | PASS | PASS | `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md`; `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |

The individual `test_sample_*.json` files contain 104 encoded input features and additional values needed by the proof runner. They should be cited by path or summarized as above, not reproduced in the thesis appendix.

## A.10 Negative-Test and Adversarial-Test Matrix

| Test | Manipulated value or condition | Expected failure layer | Observed result | Evidence source |
|---|---|---|---|---|
| Wrong public `y_hat` | Flip the public prediction | witness-generation failure caused by a circuit-constraint failure | Rejected for the reported samples | `stage3_zk/scripts/stage 3.4/test_stage34_negative.py`; `stage3_zk/reports/STAGE34_EXACT_SHAP_SUMMARY.md` |
| Wrong top-3 group IDs | Replace rank 3 with a remaining group | witness-generation failure caused by ranking constraints | Rejected for the reported samples | `stage3_zk/scripts/stage 3.4/test_stage34_negative.py`; `stage3_zk/reports/STAGE34_EXACT_SHAP_SUMMARY.md` |
| Duplicate group IDs | Reuse an ID among the five selected/remaining IDs | witness-generation failure caused by distinctness constraints | Rejected for the reported samples | `stage3_zk/scripts/stage 3.4/test_stage34_negative.py`; `stage3_zk/reports/STAGE34_EXACT_SHAP_SUMMARY.md` |
| Out-of-range group ID | Use group ID 6 | witness-generation failure caused by `CheckGroupId` | Rejected for the reported samples | `stage3_zk/scripts/stage 3.4/test_stage34_negative.py`; `stage3_zk/reports/STAGE34_EXACT_SHAP_SUMMARY.md` |
| Manipulated `other2_ids` | Reuse a public top-3 ID as a private remaining ID | witness-generation failure caused by permutation/distinctness constraints | Rejected for the reported samples | `stage3_zk/scripts/stage 3.4/test_stage34_negative.py`; `stage3_zk/reports/STAGE34_EXACT_SHAP_SUMMARY.md` |
| Private input range violation | Set `x_shifted[0] = 2*maxAbsX + 1` | witness-generation failure caused by the private-input range constraint | Rejected for the reported samples | `stage3_zk/scripts/stage 3.4/test_stage34_negative.py`; `stage3_zk/reports/STAGE34_EXACT_SHAP_SUMMARY.md` |
| Wrong verification key | Verify the current sample-1 proof with another stage's vkey | Groth16 verification rejection | Read-only audit command returned `Invalid proof` | Current SnarkJS audit command; `tools/verify_stage34_policy.py` identifies the normal verifier path |
| Wrong circuit/model artifact | Change an approved artifact hash or a public model signal | verifier-policy rejection | Rejected by self-test | `python tools/verify_stage34_policy.py --self-test`; policy verifier |
| Registry digest mismatch | Supply an unapproved combined digest | verifier-policy rejection | Rejected by self-test | `python tools/verify_stage34_policy.py --self-test`; policy verifier |
| Changed public signal after proof generation | Modify a public signal while retaining the original proof | Groth16 verification rejection | not implemented as a dedicated persisted Stage 3.4 proof-layer test; the self-test rejects a changed public model signal earlier at policy level | Policy verifier; A.13 G6 |

The six witness-mutation tests are reported as witness-generation failures. This is the appropriate rejection layer because an invalid witness cannot proceed to proof generation. The stored summary states coverage for samples 1-8, but it does not preserve a separate machine-readable result record for every sample/mutation pair.

The reference vector and semantic-group map cannot be altered through witness input because they are embedded in the circuit. Changing either requires a different circuit artifact, which must then fail the approved registry hash/digest policy unless explicitly registered.

Implemented verifier-policy commands:

```text
python tools/verify_stage34_policy.py
python tools/verify_stage34_policy.py --self-test
```

## A.11 Verifier Policy and Artifact Binding

The Stage 3.4 verifier policy checks that the accepted public model artifacts, circuit source, and verification key match a local registry before Groth16 verification.

| Bound artifact | Path | Hash or registry field | Policy check |
|---|---|---|---|
| Public Logistic Regression model and quantization configuration | `stage3_zk/artifacts/model_public.json` | SHA-256 `0055e2d36375c49093917ddfe235050610b82d5fe29c39872461aada5ecb1c40` | File hash plus public model-signal prefix |
| Feature order | `stage3_zk/artifacts/feature_order.json` | SHA-256 `7aab99865e47fb6d4d0905a0050845ea4595e60f615c6594200ab64128dabdcc` | File hash |
| Semantic group map | `stage3_zk/artifacts/group_map.json` | SHA-256 `0d4262b101371dd47c90c81782955025117ad464e98943defa2f32ebb0c23d31` | File hash |
| Bounds | `stage3_zk/artifacts/bounds.json` | SHA-256 `c534c3f4d7814c34fbe19c6accf6ab20ce9326b800cc06473da2c0e7ec78c143` | File hash; circuit constants are separately parsed |
| Exact SHAP reference and input scale | `stage3_zk/artifacts/exact_shap_reference.json` | SHA-256 `b9bae6eb00690b03d6ac3602e6aa006f96b0fd12a48f2db3982b03ff818fe21e` | File hash |
| Stage 3.4 circuit | `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom` | SHA-256 `27452d3b4f8495c158ee53f414dc8b4574f1cd946886aef4988c58bc37bcb9e5` | File hash plus fixed-parameter parsing |
| Verification key | `stage3_zk/circuits/exact_shap_top3/build/verification_key.json` | SHA-256 `6e06e219d733f6a692aac52d9c77005b3e52753ddbf4ba9913db43e29a6f699f` | File hash and Groth16 verification input |
| Approved artifact set | `stage3_zk/artifacts/model_registry_stage34.json` | `combined_sha256` | Recomputed combined digest must equal the approved digest |

Approved combined digest:

```text
6c3c9e086aceb1f2a0038c1c3726baf49998a310fcd64421b98cadaf39e32b14
```

Current policy sequence, as implemented by `tools/verify_stage34_policy.py`:

1. Load the local registry and recompute each registered file hash.
2. Recompute the combined digest and compare it with the approved digest.
3. Parse fixed circuit parameters and compare public model signals against the registered artifacts.
4. Check public-signal length, binary `y_hat`, and distinct valid top-3 group IDs.
5. Invoke SnarkJS Groth16 verification with the registered verification key.

Any failed hash, digest, public-signal, or Groth16 check causes local verification to return failure and the proof is not accepted by the policy script.

A read-only normal policy run during this audit accepted the current sample-1 proof. The self-test accepted the positive case and rejected a wrong combined digest, wrong artifact hash, wrong public model signal, and duplicate public top-3 IDs.

The prototype implements verifier-side binding to an approved artifact set through a registry artifact and combined digest. It does not implement a distributed or production-grade model-registry service. The registry is a repository JSON artifact, verification is local, and the public model is not confidential. The policy also does not provide provenance authority, ingestion authenticity, or replay protection.

## A.12 Minimal Evidence Paths for Examiner Inspection

The following 15 paths form a compact examiner-facing evidence set. Binary build outputs and full witness/proof/public vectors are intentionally excluded.

| Evidence purpose | Recommended repository path |
|---|---|
| Final-number precedence | `reports/final_numbers_source_of_truth.md` |
| Dataset protocol | `reports/dataset_summary.md` |
| Environment reproducibility | `requirements-ml.lock.txt` |
| Main Stage 3.4 relation | `stage3_zk/circuits/exact_shap_top3/exact_shap_top3.circom` |
| Input preparation and off-circuit ordering | `stage3_zk/scripts/stage 3.4/01_prepare_input_stage34.py` |
| Circuit compilation | `stage3_zk/scripts/stage 3.4/02_compile_circuit_stage34.ps1` |
| Setup, witness, prove, verify, and report orchestration | `stage3_zk/scripts/stage 3.4/04_run_phase_c_stage34.py` |
| Current proof metrics and PASS evidence | `stage3_zk/reports/STAGE34_PROOF_REPORT.md` |
| Diverse sample selection | `stage3_zk/reports/STAGE34_DIVERSE_TEST_VECTORS.md` |
| Negative tests | `stage3_zk/scripts/stage 3.4/test_stage34_negative.py` |
| Approved artifact registry | `stage3_zk/artifacts/model_registry_stage34.json` |
| Verifier policy implementation | `tools/verify_stage34_policy.py` |
| Quantization agreement | `reports/float_vs_quantized_lr_agreement.md` |
| Ranking-margin analysis | `reports/exact_shap_ranking_margin.md` |
| Supplemental Stage 3.4 batch smoke evidence | `stage3_zk/reports/STAGE34_BATCH_SMOKE_REPORT.md` |

Do not reproduce these generated artifacts in the thesis document:

- R1CS, WASM, zkey, `.wtns`, `.sym`, or Powers of Tau binaries.
- Full proof JSON, public-signal JSON, witness vectors, or the eight full encoded input vectors.
- `node_modules/`, package caches, model binaries, or raw dataset files.
- Historical benchmark directories when the current source-of-truth report is available.

For thesis presentation, include selected circuit excerpts from A.6, the proof summary from A.8, the sample manifest from A.9, the negative-test matrix from A.10, and the registry digest/policy boundary from A.11. Cite repository paths for the rest.

## A.13 Reproducibility Gaps and Audit Notes

| Issue | Severity | Evidence | Recommended correction |
|---|---|---|---|
| G1: Active Python packages do not exactly match `requirements-ml.lock.txt`, and the documented baseline environment is Python 3.10 while the audit environment is Python 3.12.3. | important | Active scikit-learn is 1.5.1 versus locked 1.4.2; active XGBoost is 3.0.5 versus locked 3.1.2. | Re-run final ML report generation in the locked environment; archive `python --version` and the resolved package versions. |
| G2: No single canonical environment bootstrap command is documented. | important | Lock files exist, but README instructions assume pre-existing Conda and Node environments. | Add exact environment-creation, locked installation, Node installation, and WSL Circom verification commands. |
| G3: `stage3_zk/artifacts/bounds.json` contains a stale or differently scoped `max_abs_score_int`. | important | The JSON value 22,988,183,559 is below valid selected Stage 3.4 score magnitudes, while the circuit enforces `B = 68,719,476,736`. Registry verification checks file identity but not this semantic consistency. | Correct or relabel the field, regenerate the registry and approved digest, and rerun policy/proof evidence. |
| G4: The Groth16 setup is a local proof-of-concept setup with one local contribution. | important | The runner uses fresh entropy, but no multiparty ceremony or independently verifiable ceremony transcript is documented. | State the prototype scope; deployment would require a documented production setup process. |
| G5: Canonical tie-breaking is not enforced inside the circuit. | informational | The circuit enforces non-increasing magnitudes; smaller-ID tie-breaking occurs in input preparation only. | Describe exact ties as permitting multiple valid orders, or add an in-circuit deterministic tie-break before claiming canonical ordering. |
| G6: Negative-test evidence is not fully persisted at the proof layer. | minor | Six witness mutations are summarized for samples 1-8, but per-sample machine-readable logs and a dedicated changed-public-signal-after-proof test were not found. | Save a result matrix with sample, mutation, failure layer, exit code, and expected outcome; add a direct modified-public-signal Groth16 test. |
| G7: Historical and current timing artifacts coexist. | informational | Older Node-API timing and supporting benchmarks can be confused with current eight-sample CLI evidence. | Keep the source-of-truth report prominent, label historical reports, and use only `stage3_zk/reports/STAGE34_PROOF_REPORT.md` for current Stage 3.4 timing. |
| G8: The Stage 3.4 compile script contains a machine-specific absolute WSL checkout path. | important | `stage3_zk/scripts/stage 3.4/02_compile_circuit_stage34.ps1:24` changes to a hard-coded checkout location; another checkout location will fail without editing the script. | Derive the WSL circuit directory from the PowerShell script location and pass the converted path to WSL. |

Unresolved audit-gap count: **8**. None invalidates the current functional Stage 3.4 proof evidence, but G1-G4 and G8 should be addressed or explicitly scoped before final thesis archival.

## A.14 Final Audit Checklist

| Check | Status | Evidence or note |
|---|---|---|
| Authoritative final-number map identified | PASS | `reports/final_numbers_source_of_truth.md` |
| Dataset mode, split, seed, and counts identified | PASS | Dataset report and split metadata |
| Main Stage 3.4 circuit located and excerpted | PASS | A.6 |
| Circuit compilation toolchain identified | PASS | WSL Circom 2.2.3; source pragma 2.1.9; compile script |
| Current compiled R1CS metadata inspected | PASS | 8,358 constraints; 8,078 wires; 109 public; 106 private |
| Verification key located and size verified | PASS | 22,669 bytes; registry record |
| Registry hashes and combined digest verified | PASS | Normal verifier-policy run during audit |
| Samples 1-8 witness/proof/verification evidence located | PASS | Proof report and sample reports |
| Functional TP, TN, FN, FP, confidence, threshold, and margin cases covered | PASS | A.9 |
| Implemented negative tests located and summarized | PASS | A.10 |
| Supplemental 30-sample Stage 3.4 batch smoke evidence located | PASS | `stage3_zk/reports/STAGE34_BATCH_SMOKE_REPORT.md` |
| Public/private signal boundary stated without calling public inputs Circom outputs | PASS | A.5 |
| Exact SHAP reference visibility and origin stated | PASS | Hardcoded quantized training mean |
| Quantization and range constraints summarized | PARTIAL | A.7; stale `stage3_zk/artifacts/bounds.json` score field recorded as G3 |
| Historical timing excluded from current Stage 3.4 summary | PASS | A.4 and A.8 |
| Stage 3.5 excluded from the main Stage 3.4 claim | PASS | Appendix-only row in A.4 |
| Witness values, full public vectors, proof JSON, and binary artifacts excluded | PASS | A.12 |
| All cited paths are repository-relative | PASS | Final path audit |
| Repository files modified beyond this requested evidence package | PASS | No other repository file intentionally modified by this audit |

The evidence package is ready to support a concise thesis appendix after the author decides whether to resolve G1-G4 before final submission. It supports the implemented Stage 3.4 relation only and must not be used to claim confidential-model verification, model-agnostic SHAP, differential privacy, source-event provenance, or production deployment readiness.
