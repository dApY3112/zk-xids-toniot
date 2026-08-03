# Thesis Handoff Summary and Full Outline

**Working title:** *Zero-Knowledge Framework for Verifiable Semantic Explanations under Private Input: An Intrusion Detection Case Study*  
**Current thesis status:** Chapters 3, 4, and 5 have been drafted. Chapters 1, 2, 6, 7, and 8 still need to be written or finalized. Since the first draft of this handoff, Stage 3.5 has been added as an appendix-only input-commitment prototype.

---

## 1. Core Thesis Scope

The thesis proposes and evaluates a **public-model/private-input framework for verifiable semantic explanations**. The general purpose is to allow a verifier to check that both a model prediction and its semantic explanation were computed from the same private input, without revealing the input feature vector.

The implemented system does **not** aim to hide the model. The model is public, approved, and auditable. The private object is the processed input feature vector. The verifier intentionally learns the prediction and the ordered top-3 semantic group identifiers, but not the full processed input or the exact semantic-group SHAP magnitudes.

Correct scope claim:

> The thesis studies input-feature privacy and explanation authenticity under an approved public model.

Incorrect claims to avoid:

- hidden-model support;
- confidential-model proofs;
- arbitrary-model SHAP;
- Partition SHAP;
- sumcheck/GKR implementation;
- XGBoost-in-ZK;
- full SIEM/log-row provenance binding as a completed deployment feature;
- complete behavioral secrecy;
- production-ready deployment.

Stage 3.5 status:

- An optional Stage 3.5 appendix prototype implements a Poseidon input-commitment check.
- It demonstrates that the private witness can be bound to a public commitment signal.
- It is not a full provenance system by itself, because full provenance also requires a trusted ingestion-time commitment registry, replay policy, metadata schema, and deployment trust model.
- Treat Stage 3.5 as appendix evidence, not as the main thesis claim.

---

## 2. Meaning of ZK-XIDS

In the thesis, **ZK-XIDS** should refer to the **intrusion detection case-study implementation**, not to a separate general framework.

Recommended wording:

> In this thesis, ZK-XIDS refers to the case-study implementation used to evaluate the proposed public-model and private-input framework, rather than to a separate general framework.

Use these terms consistently:

| Term | Recommended meaning |
|---|---|
| The proposed framework | The general public-model/private-input verification framework |
| The implemented system | The concrete implementation built in the thesis |
| ZK-XIDS case study | The IDS case-study instantiation using TON_IoT |
| Stage 3.4 implementation | The implemented Exact SHAP top-3 proof relation |
| Stage 3.5 appendix prototype | Optional input-commitment feasibility extension, not the main system claim |

Avoid calling it "the ZK-XIDS framework" unless the phrase clearly means the IDS prototype.

---

## 3. Writing Order and Reference Strategy

Do **not** start with Chapter 1 or Chapter 2. Those chapters require the most references and should be finalized later.

Recommended writing order:

1. Chapter 5 - already drafted; polish and verify.
2. Chapter 6 - write next as the core methodology/formal framework chapter.
3. Chapter 7 - write after Chapter 6 as the evaluation and evidence chapter.
4. Chapter 8 - draft after Chapter 7.
5. Chapter 2 - write later after references are collected.
6. Chapter 1 - write near the end.
7. Abstract - write last.

When writing before all references are collected:

- Use citation placeholders such as `[TODO: cite Groth16]`, `[TODO: cite ZKP]`, or `[TODO: cite ZKML]`.
- Do not invent references.
- Project-specific results, artifact names, and experimental values do not require external citations, but they must be described accurately.
- External references are needed when discussing established methods, related work, datasets, or theory.

---

# 4. Current Draft Summary: Chapter 3

## Chapter 3: Research Design and System Overview

### Purpose

Chapter 3 explains the research design, the system-level framework, information visibility assumptions, and how the general idea is instantiated in the IDS case study.

### 3.1 Research Design

Current content:

- The thesis follows a design-oriented and experimental research approach.
- It designs, implements, and evaluates a verification mechanism for semantic explanations under private inputs.
- The research combines three layers:
  1. machine learning pipeline for intrusion detection;
  2. semantic explanation layer;
  3. zero-knowledge proof layer.
- The implementation is an IDS case study, but the design is formulated more generally for tabular classification with public/auditable models, private inputs, and fixed semantic groups.
- The concrete instantiation uses:
  - TON_IoT dataset;
  - public Logistic Regression classifier;
  - five semantic groups;
  - Circom/Groth16 proofs.
- The final implemented relation verifies ordered top-3 semantic-group Exact SHAP for the public Logistic Regression model.
- The chapter clarifies the separation between model-performance evaluation and proof-system evaluation.

Recommended final point:

> This separation is important because the strongest plaintext model is not necessarily the most suitable model for zero-knowledge verification.

### 3.2 System Objective and Information Visibility

Current content:

- The system objective is to allow a verifier to check whether a released IDS decision and semantic explanation were computed correctly from the same private input.
- The prover holds a processed network-flow feature vector.
- The proof is generated with respect to an approved public Logistic Regression model.
- The verifier interprets the prediction and ordered top-3 semantic group identifiers as certified outputs.
- The visibility setting is public-model/private-input.

Core visibility assumptions:

| Component | Visibility |
|---|---|
| Logistic Regression weights and bias | Public model artifact |
| Feature order, semantic group map, and bounds | Public fixed artifacts |
| Processed input vector `x_shifted[104]` | Private witness |
| Prediction `y_hat` | Public output |
| Ordered top-3 semantic group IDs | Public output |
| Semantic-group Exact SHAP values `phi_g` | Private intermediate |
| Reference vector `x_ref` | Fixed public artifact |
| Groth16 proof `pi` | Public proof object |
| Verification key | Public verification artifact |
| Model registry digest / approved model ID | Public policy-level metadata |

Current Table 3.1:

> Table 3.1. Public and private information in the implemented system.

Main claim:

> The verifier learns the prediction and ordered top-3 semantic explanation, but not the processed feature vector or the exact semantic-group SHAP magnitudes.

The model registry/policy layer records the approved public model version and associated artifacts. It does not hide the model. It ensures that a valid proof is interpreted with respect to the correct model, feature order, semantic group map, reference vector, circuit version, and verification key.

### 3.3 Framework Overview

Current content:

- The system is described as a workflow between prover and verifier.
- The prover holds the private processed input.
- The prover computes the IDS output and semantic explanation.
- The prover generates a Groth16 proof.
- The verifier checks the proof and approved public artifacts before accepting the released prediction and explanation.

Current Figure 3.1:

> Figure 3.1. System-level overview of the proposed public-model and private-input framework for verifiable semantic explanations.

Figure content:

- public artifacts/policy;
- prover side;
- private input `x_shifted[104]`;
- prover computation;
- prediction `y_hat` public;
- top-3 group IDs public;
- Exact SHAP ranking private;
- Groth16 proof;
- verifier side;
- proof and policy checks;
- certified IDS decision and explanation.

Core explanation:

- The same private input is used for both prediction and explanation.
- Exact SHAP values are used internally for ranking and are not released.
- The proof prevents the prediction and explanation from being independent metadata supplied by the prover.

### 3.4 IDS Case Study and Reproducibility Strategy

Current content:

- The system is instantiated through the ZK-XIDS IDS case study.
- ZK-XIDS is defined as the case-study implementation, not a separate general framework.
- The empirical setting is based on TON_IoT.
- The task is binary classification between normal and attack traffic.
- The case study has two purposes:
  1. provide a realistic tabular security setting for ML and semantic explanations;
  2. test whether a prediction and explanation can be verified without revealing processed input features.
- The case study uses:
  - public Logistic Regression model;
  - fixed 104-feature input representation;
  - private processed network-flow vector.

Current Table 3.2:

> Table 3.2. Mapping between the general framework and the IDS case study.

Recommended mapping:

| Framework component | IDS case study instantiation |
|---|---|
| Private tabular input | Processed TON_IoT network-flow feature vector `x_shifted[104]` |
| Approved public model | Public Logistic Regression intrusion detection model |
| Semantic groups | Protocol, Application, ConnectionState, Ports, TrafficVolume |
| Semantic explanation | Ordered top-3 semantic groups derived from semantic-group Exact SHAP |
| Proof system | Circom/Groth16 proof for the implemented verification relation |
| Verifier policy | Approved model, feature order, group map, bounds, reference vector, circuit version, and verification key |
| Certified output | Intrusion detection decision and ordered top-3 semantic explanation |

Reproducibility artifacts:

- dataset split;
- preprocessing schema;
- feature order;
- trained model artifacts;
- semantic group map;
- quantization bounds;
- reference vector;
- circuit version;
- verification key.

### Chapter 3 cleanup notes

Needed edits:

- Change "The main components of the proposed framework is shown" to "Figure 3.1 summarizes the main components of the proposed framework."
- Keep captions short and consistent.
- Make sure all mathematical symbols are formatted consistently in Word.
- Prefer `x_shifted[104]`, `y_hat`, and `phi_g` in body text if Equation Editor formatting becomes inconsistent.
- Use `TON_IoT`, not `TON_IOT`.
- Do not add formal theorem or relation details here. Those belong to Chapter 6.

---

# 5. Current Draft Summary: Chapter 4

## Chapter 4: Dataset, Preprocessing, and Baseline Models

### Purpose

Chapter 4 describes the empirical and machine learning foundation of the ZK-XIDS case study. It connects the system overview from Chapter 3 to the concrete dataset, preprocessing artifacts, baseline models, and model-selection rationale.

### Chapter opening

Current content:

- Chapter 3 explained the framework and how private input, public model, semantic explanation, and ZK proof are connected.
- Chapter 4 shifts to the data and ML pipeline.
- The proof layer depends on earlier ML artifacts:
  - feature order;
  - trained model;
  - semantic group map;
  - value bounds.

Current Figure 4.1:

> Figure 4.1. Dataset preparation and baseline modeling pipeline used in the ZK-XIDS case study.

Figure content:

- TON_IoT processed network files;
- sampling and split;
- preprocessing;
- fixed 104-feature representation;
- train models;
- evaluation;
- exported artifacts.

### 4.1 Dataset and Experimental Protocol

Current content:

- Dataset: TON_IoT Network dataset.
- Citation: Alsaedi et al. (2020).
- Task: binary classification, Normal vs Attack.
- The dataset is used for model training/evaluation and later as private tabular inputs for the ZK framework.
- The pipeline uses processed TON_IoT network files rather than raw traffic logs.
- The data are organized into 23 processed CSV files.
- Sampling: 15% from each processed file.
- Random seed: 42.
- Dataset mode: `processed_stratified_sample_23files_frac0.15`.
- Meaning of the dataset mode:
  - processed files are used;
  - sampling is stratified;
  - 23 files are included;
  - sampling fraction is 0.15.
- Data split: stratified train/validation/test.
- Class imbalance:
  - Attack is majority;
  - Normal is minority.
- Leakage-prone fields excluded:
  - `src_ip`;
  - `dst_ip`;
  - `type`.

Current Table 4.1:

> Table 4.1. Summary of the dataset and experimental protocol.

### 4.2 Preprocessing and Feature Freezing

Current content:

- The preprocessing stage converts sampled TON_IoT data into a model-ready tabular representation.
- Original processed files contain numeric, categorical, and boolean fields.
- These fields are transformed into a consistent numerical feature matrix.
- Final representation has 104 features.
- Feature order is frozen before model training and explanation analysis.
- Freezing is necessary because LR weights, semantic group map, and ZK circuit inputs must refer to the same feature indices.

Current Table 4.2:

> Table 4.2. Main preprocessing artifacts and their roles.

Artifacts:

- preprocessing pipeline;
- feature schema;
- feature names;
- feature order;
- processed training/validation/test arrays;
- exported ZK feature order.

### 4.3 Baseline Models and Imbalance-Aware Metrics

Current content:

- Two baseline models are used:
  - Logistic Regression;
  - XGBoost.
- Logistic Regression is linear, interpretable, and proof-compatible.
- XGBoost is a stronger non-linear plaintext baseline.
- Accuracy alone is insufficient due to class imbalance.
- Metrics used:
  - accuracy;
  - balanced accuracy;
  - Matthews correlation coefficient;
  - Attack recall;
  - Normal recall / specificity;
  - false positive rate;
  - PR-AUC mentioned in prose, but not necessarily included in compact Table 4.3.

Current Table 4.3:

> Table 4.3. Baseline evaluation metrics used under class imbalance.

### 4.4 Baseline Results and Logistic Regression Selection

Current content:

- XGBoost is the stronger plaintext IDS model.
- Logistic Regression performs reasonably but is weaker under class imbalance.
- Logistic Regression is selected for the proof layer because its prediction is based on a linear score.
- The linear structure supports compact circuit constraints and closed-form semantic-group Exact SHAP.
- This is a trade-off between predictive strength and verifiability.

Current Table 4.4:

> Table 4.4. Imbalance-aware baseline performance on the test set.

Current compact metrics:

| Model | Balanced accuracy | MCC | Attack recall | Normal recall | FPR |
|---|---:|---:|---:|---:|---:|
| XGBoost | 0.992132 | 0.98685 | 0.999631 | 0.984634 | 0.015366 |
| Logistic Regression | 0.923103 | 0.53582 | 0.935017 | 0.911189 | 0.088811 |

Interpretation:

- XGBoost has lower FPR and higher Normal recall.
- Logistic Regression has weaker performance, especially in MCC.
- XGBoost is retained as a strong plaintext reference.
- Logistic Regression is used as the proof-compatible model.

### Chapter 4 cleanup notes

Needed edits:

- Replace "Figure 4.1 indicates" with "Figure 4.1 summarizes".
- Replace "It can be seen from table 4.1 that..." with "Table 4.1 summarizes..."
- Replace "Table summarizes..." in 4.3 with "Table 4.3 summarizes..."
- If using numeric references, change `(Alsaedi et al., 2020)` to `[1]`, or make references consistently Harvard style.
- Do not add ROC, PR, calibration, or drift figures in Chapter 4. Save those for Chapter 7 or appendix.

---

# 6. Current Draft Summary: Chapter 5

## Chapter 5: Semantic Explainability and Group-Level Attribution

### Purpose

Chapter 5 explains the explanation layer before the formal zero-knowledge framework. It moves from raw feature-level attribution to semantic-group explanations and then motivates semantic-group Exact SHAP as the stronger target for later verification.

### Chapter opening

Current content:

- Chapter 4 established the empirical basis of the ZK-XIDS case study.
- Predictions alone are not enough in IDS.
- Security analysts may need to understand which parts of the input influenced a decision.
- Explanations are first studied at raw feature level and then lifted to semantic groups.
- The chapter introduces:
  1. raw top-k feature attribution;
  2. raw stability and model overlap;
  3. semantic group construction;
  4. semantic stability and group-level overlap;
  5. group frequency and group-size bias;
  6. transition from attribution proxy to semantic-group Exact SHAP.

### 5.1 Raw Top-k Feature Attribution

Current content:

- Raw feature-level attribution is used to identify the top features contributing to individual predictions.
- This is a local explanation, not a global model summary.
- Logistic Regression is explained using absolute linear contribution.
- XGBoost is explained using contribution outputs from `pred_contribs=True`.
- Top-5 raw features are selected per sample.
- The same `k = 5` is used for both models.
- The analysis is performed on 1100 samples from the Stage 2 explanation subset.

Current Table 5.1:

> Table 5.1. Raw attribution methods used for baseline models.

Recommended table:

| Model | Raw attribution score | Role in the analysis |
|---|---|---|
| Logistic Regression | Absolute linear contribution, `|w_i x_i|` | Deterministic linear attribution proxy |
| XGBoost | Absolute contribution from `pred_contribs=True` | Tree-based comparison baseline |

References currently used:

- [4] Molnar for general local feature attribution / interpretability.
- [2] Chen and Guestrin for XGBoost.
- [3] Lundberg and Lee for SHAP-like tree contributions.

### 5.2 Raw Feature Stability and Model Overlap

Current content:

- Raw top-k explanations are inspected for consistency.
- Two diagnostics:
  1. within-model stability;
  2. between-model overlap.
- Stability is measured using mean pairwise Jaccard similarity of top-5 feature sets.
- Between-model overlap is measured by Jaccard overlap between LR and XGBoost top-5 sets.

Current values:

| Measure | Value |
|---|---:|
| Logistic Regression raw stability | 0.5847 |
| XGBoost raw stability | 0.4075 |
| Logistic Regression-XGBoost raw overlap | 0.1558 |
| Raw overlap standard deviation | 0.0820 |

Interpretation:

- Logistic Regression explanations are more consistent at raw feature level.
- XGBoost explanations vary more across samples.
- Raw feature-level explanations are detailed but fragmented and model-dependent.

Current Table 5.2:

> Table 5.2. Raw top-5 explanation stability and model overlap.

### 5.3 Semantic Group Construction

Current content:

- Raw feature explanations are too detailed for a compact explanation interface.
- The 104 processed features are mapped into five semantic groups.
- The model still operates on the full 104-feature input.
- The explanation layer reports which semantic groups are most influential.
- The semantic group mapping is fixed before proof generation.
- The same feature index must keep the same meaning across preprocessing, inference, explanation, and circuit input preparation.

Current Figure 5.1:

> Figure 5.1. Semantic grouping pipeline from processed features to five explanation groups.

Current Table 5.3:

> Table 5.3. Semantic groups used in the explanation layer.

Semantic groups:

| Semantic group | Description | Example feature types |
|---|---|---|
| Protocol | Network protocol indicators | `proto_tcp`, `proto_udp`, `proto_icmp` |
| Application | Service, HTTP, SSL, and diagnostic indicators | `service_*`, `http_*`, `ssl_*`, `weird_name_*` |
| ConnectionState | Connection state indicators | `conn_state_*` |
| Ports | Source and destination port fields | `src_port`, `dst_port` |
| TrafficVolume | Flow size and traffic volume features | `duration`, `src_bytes`, `dst_bytes`, `src_pkts`, `dst_pkts` |

### 5.4 Semantic Stability and Group-Level Overlap

Current content:

- After mapping raw features to semantic groups, the same stability and overlap diagnostics are computed at group level.
- Semantic grouping improves stability and overlap.

Current values:

| Measure | Raw feature level | Semantic group level |
|---|---:|---:|
| Logistic Regression stability | 0.5847 | 0.7794 |
| XGBoost stability | 0.4075 | 0.7429 |
| Logistic Regression-XGBoost overlap | 0.1558 | 0.3012 |

Interpretation:

- Semantic grouping reduces fragmentation.
- It does not make the two models identical, but it gives a smaller and more readable explanation space.
- The later verification layer uses ordered top-3 ranking over five semantic groups.

Current Table 5.4:

> Table 5.4. Raw and semantic-level stability and overlap.

### 5.5 Group Frequency and Group-Size Bias

Current content:

- Semantic groups have unequal sizes.
- Application contains 76 features.
- Ports contains 2 features.
- Protocol contains 3 features.
- Raw group frequency can be biased by group size.
- A large group has more chances to appear in top-k explanations.
- Size-normalized view is used as a diagnostic check.

Current patterns:

| Model | Raw top-3 groups | Size-normalized top-3 groups |
|---|---|---|
| Logistic Regression | Application, Protocol, ConnectionState | Protocol, ConnectionState, Ports |
| XGBoost | TrafficVolume, Ports, Protocol | Ports, Protocol, TrafficVolume |

Interpretation:

- Application frequency in LR must be interpreted together with group size.
- Group-size analysis does not replace semantic grouping.
- It makes the limitation explicit.
- The proof system verifies ordered top-3 groups for a given input and model relation; it does not claim that group frequency alone is a complete measure of explanation quality.

Current Table 5.5:

> Table 5.5. Raw and size-normalized semantic group frequency patterns.

### 5.6 From Attribution Proxy to Semantic-Group Exact SHAP

Current content:

- Semantic grouping creates a smaller explanation space, but does not define how group importance is computed.
- Earlier implementation used grouped attribution proxy:

```text
sum_{i in G_g} |w_i x_i|
```

- This proxy is deterministic, simple, and proof-friendly.
- However, it is not a Shapley-value explanation.
- It measures absolute weighted feature magnitude relative to the feature origin.
- It does not measure marginal contribution relative to a background/reference input.
- Semantic-group Exact SHAP is selected as the stronger explanation target.

Current Figure 5.2:

> Figure 5.2. Transition from the grouped attribution proxy to semantic-group Exact SHAP.

Exact SHAP explanation:

- Semantic groups are treated as players in a cooperative game.
- Contribution is measured by comparing model score when a group is included versus removed.
- The value function is the Logistic Regression score/logit, not probability.
- Removed groups are replaced by the feature-wise training-set mean.
- Only five semantic groups are used, so exact enumeration is feasible outside the circuit.
- Chapter 6 formalizes the proof relation and explains the closed form.

References currently used:

- [5] Shapley for Shapley values.
- [3] Lundberg and Lee for SHAP.

### 5.7 Chapter Summary

Current content:

- Chapter 5 described the explanation layer before zero-knowledge verification.
- It examined raw top-k feature attribution for LR and XGBoost.
- It showed why raw feature explanations are too detailed and fragmented.
- It mapped 104 features into five semantic groups.
- It discussed group-size bias.
- It positioned the grouped attribution proxy as an engineering baseline, not a Shapley-value explanation.
- It motivated semantic-group Exact SHAP as the stronger target for Chapter 6.

### Chapter 5 cleanup notes

Needed edits:

- Ensure all table and figure captions have a period after the number, e.g., `Table 5.1.`
- Ensure all figures are referenced before or near their placement.
- Check mathematical notation in Word: `|w_i x_i|`, `w_i`, `x_i`, `phi_g`, and `G_g` should be formatted consistently.
- Keep Chapter 5 as an explanation-design chapter, not a proof-design chapter.
- Do not add circuit constraints, proof cost, or negative tests here. Those belong to Chapters 6 and 7.

---

# 7. Full Thesis Outline

## Chapter 1: Introduction

### Purpose

Introduce the motivation, problem, research gap, research questions, contributions, scope, and thesis structure. Write this chapter near the end, after Chapters 6 and 7 are stable.

### Suggested sections

#### 1.1 Background and Motivation

Content:

- Machine learning is used for intrusion detection and other tabular decision tasks.
- Explanations can support trust, auditability, and security analysis.
- Network-flow features can be sensitive.
- A verifier may need to check outputs without seeing private input features.
- General motivation: move from explainable AI outputs to verifiable explanations.

#### 1.2 Problem Statement and Research Gap

Content:

- A prediction and explanation can be released as metadata, but the verifier may not know whether they were computed from the same private input.
- Existing XAI often focuses on generating explanations, not cryptographically verifying them.
- ZKML often focuses on verifying predictions, while explanation authenticity is less explored.
- Hidden-model ZKML is adjacent work, but this thesis studies a different threat model: public model and private input.

#### 1.3 Research Aim and Research Questions

Possible RQs:

- RQ1: Can private-input tabular inference be verified without revealing processed features in an IDS setting?
- RQ2: Can semantic explanations be verified cryptographically rather than trusted as client-supplied metadata?
- RQ3: Can semantic-group Exact SHAP be made feasible in a SNARK for an approved public Logistic Regression model?
- RQ4: What overhead and limitations arise when moving from an engineering attribution proxy to verified Exact SHAP?

#### 1.4 Contributions

Possible contributions:

- A public-model/private-input framework for verifiable semantic explanations.
- A semantic-group abstraction for tabular IDS explanations.
- A Stage 3.4 Groth16 relation verifying ordered top-3 semantic-group Exact SHAP for public Logistic Regression.
- A reproducible IDS case-study evaluation covering ML performance, explanation stability, proxy-vs-ExactSHAP behavior, ML-to-ZK quantization agreement, ranking-margin self-assessment, proof correctness, proof cost, output leakage, reference sensitivity, and an appendix-only input-commitment feasibility prototype.

#### 1.5 Scope and Thesis Structure

Content:

- Public-model/private-input scope.
- ZK-XIDS is case-study implementation, not general framework name.
- Full provenance deployment, hidden-model support, Partition SHAP, sumcheck/GKR, and XGBoost-in-ZK remain future work.
- Stage 3.5 input commitment is already implemented as an appendix feasibility prototype, but it should not be presented as complete external log provenance.
- Brief summary of each chapter.

Expected figures/tables:

- Usually none.

Status:

- Not written yet.

---

## Chapter 2: Background and Related Work

### Purpose

Provide theoretical and literature foundation. This chapter needs the most references.

### Suggested sections

#### 2.1 Machine Learning and Intrusion Detection

Content:

- IDS basics.
- ML-based IDS.
- TON_IoT or IoT/IIoT IDS context.
- Model performance and imbalance issues.

#### 2.2 Explainable AI and Feature Attribution

Content:

- Why explanations are useful.
- Local and global explanations.
- SHAP, Shapley values, and feature attribution.
- Group-level explanations as readable abstraction.

#### 2.3 Zero-Knowledge Proofs and zk-SNARKs

Content:

- Public statement and private witness.
- Proof and verification.
- Groth16 at high level.
- Keep explanation readable, not too cryptographic.

#### 2.4 Verifiable Machine Learning and Verifiable Explanations

Content:

- ZKML prediction verification.
- Hidden-model and private-input variants.
- ExpProof or related verifiable explanation work if relevant.
- Position this thesis as public-model/private-input explanation verification.

#### 2.5 Summary of Research Gap

Content:

- Existing XAI: explanation generation but not proof-bound authenticity.
- Existing ZKML: often prediction verification or hidden-model focus.
- This thesis: verifies semantic explanation authenticity under private input with approved public model.

Expected figures/tables:

- Optional related-work comparison table.

Status:

- Not written yet.

---

## Chapter 3: Research Design and System Overview

Status:

- Drafted.

Sections:

- 3.1 Research Design
- 3.2 System Objective and Information Visibility
- 3.3 Framework Overview
- 3.4 IDS Case Study and Reproducibility Strategy

Figures/tables:

- Table 3.1. Public and private information in the implemented system.
- Figure 3.1. System-level overview of the proposed public-model and private-input framework.
- Table 3.2. Mapping between the general framework and the IDS case study.

Next action:

- Polish grammar and formatting.
- Do not add formal proof content here.

---

## Chapter 4: Dataset, Preprocessing, and Baseline Models

Status:

- Drafted.

Sections:

- 4.1 Dataset and Experimental Protocol
- 4.2 Preprocessing and Feature Freezing
- 4.3 Baseline Models and Imbalance-Aware Metrics
- 4.4 Baseline Results and Logistic Regression Selection

Figures/tables:

- Figure 4.1. Dataset preparation and baseline modeling pipeline used in the ZK-XIDS case study.
- Table 4.1. Summary of the dataset and experimental protocol.
- Table 4.2. Main preprocessing artifacts and their roles.
- Table 4.3. Baseline evaluation metrics used under class imbalance.
- Table 4.4. Imbalance-aware baseline performance on the test set.

Next action:

- Polish grammar and cross-references.
- Keep ML plots out of Chapter 4.

---

## Chapter 5: Semantic Explainability and Group-Level Attribution

Status:

- Drafted.

Sections:

- 5.1 Raw Top-k Feature Attribution
- 5.2 Raw Feature Stability and Model Overlap
- 5.3 Semantic Group Construction
- 5.4 Semantic Stability and Group-Level Overlap
- 5.5 Group Frequency and Group-Size Bias
- 5.6 From Attribution Proxy to Semantic-Group Exact SHAP
- 5.7 Chapter Summary

Figures/tables:

- Table 5.1. Raw attribution methods used for baseline models.
- Table 5.2. Raw top-5 explanation stability and model overlap.
- Figure 5.1. Semantic grouping pipeline from processed features to five explanation groups.
- Table 5.3. Semantic groups used in the explanation layer.
- Table 5.4. Raw and semantic-level stability and overlap.
- Table 5.5. Raw and size-normalized semantic group frequency patterns.
- Figure 5.2. Transition from the grouped attribution proxy to semantic-group Exact SHAP.

Next action:

- Polish notation and table formatting.
- Keep proof details for Chapter 6.

---

## Chapter 6: Zero-Knowledge Framework for Verifiable Semantic Explanations

### Purpose

This is the core methodology/formal framework chapter. It should be technical and precise.

### Suggested sections

#### 6.1 Formal Problem Definition

Content:

- Define public statement, private witness, prover, verifier.
- Define the goal: prediction and explanation are verified from the same private input.
- Define public outputs and private values.

#### 6.2 Public-Model and Private-Input Setting

Content:

- Public artifacts:
  - LR weights and bias;
  - feature order;
  - semantic group map;
  - bounds;
  - reference vector;
  - circuit version;
  - verification key.
- Private witness:
  - `x_shifted[104]`;
  - helper top-3 identifiers if needed.
- Public outputs:
  - `y_hat`;
  - ordered top-3 group IDs.

#### 6.3 Semantic-Group Exact SHAP Definition

Content:

- Semantic groups as players.
- Coalition masking with reference vector.
- Value function is LR score/logit.
- Exact SHAP over five groups.

#### 6.4 Closed-Form Exact SHAP for Logistic Regression

Content:

- State closed form:

```text
phi_g(x) = sum_{i in G_g} w_i * (x_i - x_ref_i)
```

- Explain why it follows from linearity.
- Mention numerical validation:
  - maximum enumeration-vs-closed-form difference: `2.842171e-14`.

#### 6.5 Stage 3.4 Relation and Circuit Design

Content:

- Input range and shifted encoding.
- Recover signed input vector.
- Compute LR score.
- Compute prediction.
- Compute group-level `phi_g`.
- Compute absolute values.
- Verify valid, distinct, ordered top-3 group IDs.
- Bind prediction and explanation to same private input.

Possible table:

> Table 6.1. Public signals and private witness values in Stage 3.4.

#### 6.6 Quantization, Bounds, and Shifted Encoding

Content:

- Explain integer quantization.
- Explain `x_shifted` representation.
- Explain bounds and why they are needed.
- Avoid excessive implementation detail.

#### 6.7 Verifier Policy and Model-Version Binding

Content:

- Valid proof alone is not enough.
- Verifier must check approved artifacts.
- Model registry digest / approved model ID.
- Public model binding is not model confidentiality.

#### 6.8 Stage 3.1-3.4 Implementation Progression

Content:

- Stage 3.1: LR inference.
- Stage 3.2: grouped proxy.
- Stage 3.3: top-3 proxy verification.
- Stage 3.4: semantic-group Exact SHAP top-3 verification.

Possible figure:

> Figure 6.1. Stage progression from inference verification to Exact SHAP explanation verification.

#### 6.9 Optional Stage 3.5 Input-Commitment Appendix Prototype

Content:

- Explain the remaining Stage 3.4 provenance boundary: the proof certifies consistency with some private witness, not a specific external log row by itself.
- Present Stage 3.5 as an appendix prototype, not as the main framework claim.
- Public values: `input_commitment`, `metadata_hash`, `y_hat`, and `top3_ids`.
- Private values: `x_shifted[104]`, `salt`, and helper ranking values.
- Circuit idea:

```text
input_commitment = Poseidon(domain_tag, metadata_hash, salt, x_shifted[104])
```

- State the deployment requirement: the verifier must compare the public commitment against a trusted ingestion-time registry entry.
- Do not claim complete SIEM provenance, raw-log binding, replay resistance, or production deployment.

Possible table:

> Table 6.2. Main Stage 3.4 claim versus optional Stage 3.5 appendix prototype.

Status:

- To write next.

---

## Chapter 7: Evaluation and Results

### Purpose

Evaluate the implemented framework and provide evidence.

### Suggested sections

#### 7.1 Evaluation Setup

Content:

- Dataset mode.
- Feature count.
- Models.
- Evaluation subset.
- Stage 3.4 samples 1-8.
- Stage 3.5 appendix samples 1, 7, and 8 if included.
- Hardware/software if needed.
- Source-of-truth file for final numbers: `reports/final_numbers_source_of_truth.md`.

#### 7.2 Baseline IDS Performance

Content:

- Full baseline metrics.
- XGBoost stronger than LR.
- LR selected for proof feasibility.
- Include PR-AUC values if omitted in Chapter 4.
- Avoid presenting Logistic Regression as the strongest IDS detector; present it as the proof-compatible model.

#### 7.3 Decision Engineering, Calibration, and Drift

Content:

- Threshold behavior.
- Calibration values.
- Drift proxy.
- File-wise holdout robustness.
- Attack-type post-hoc error analysis.
- Keep figures limited; tables preferred.

Known values:

- XGB raw Brier: `0.000732`
- XGB raw ECE: `0.000271`
- XGB isotonic ECE: `0.000135`
- LR raw Brier: `0.055734`
- LR raw ECE: `0.121681`
- LR isotonic Brier: `0.013126`
- LR isotonic ECE: `0.000292`
- XGB default FPR mean: `0.014920`
- XGB MCC mean: `0.965167`
- LR default FPR mean: `0.119252`
- LR MCC mean: `0.491627`
- File-wise holdout should be described as a source-file robustness check, not true timestamp validation.
- Attack-type analysis uses `type` only after prediction, never for training.

#### 7.4 Semantic Explanation Results

Content:

- Raw and semantic stability values.
- Semantic grouping improves stability.
- Group-size bias.
- Avoid duplicating Chapter 5 too much.

#### 7.5 Exact SHAP versus Attribution Proxy

Content:

- Compare old proxy and Exact SHAP.

Known values:

- Mean top-3 overlap: `2.0618 / 3`
- Mean Jaccard overlap: `0.5407`
- Old proxy dominated by Application.
- Exact SHAP often emphasizes ConnectionState and Protocol.

Possible figures:

- Proxy vs Exact SHAP group frequency.
- Top-3 overlap distribution.

#### 7.6 ML-to-ZK Validity and Explanation Stability

Content:

- Float Logistic Regression versus quantized integer Logistic Regression agreement.
- Prediction mismatch count.
- Exact SHAP top-3 agreement and overlap.
- Rank-3 versus rank-4 margin analysis.
- Explain why this matters: the circuit proves the quantized integer relation, so the thesis must show that the quantized relation remains faithful to the trained LR model.

Known values:

| Split | Prediction agreement | Mismatches | Ordered Exact SHAP top-3 match | Mean top-3 overlap / 3 |
|---|---:|---:|---:|---:|
| Validation | 99.991246% | 44 / 502628 | 93.855694% | 2.945248 |
| Test | 99.994230% | 29 / 502628 | 93.817495% | 2.944878 |

Ranking-margin values:

| Split | Median margin | p5 margin | <=0.001 rate | <=0.01 rate |
|---|---:|---:|---:|---:|
| Validation | 0.044013 | 0.000411 | 11.172279% | 26.795165% |
| Test | 0.044013 | 0.000411 | 11.080163% | 26.811280% |

Interpretation:

- Quantized prediction agrees with float LR on more than 99.99% of validation/test rows.
- Ordered top-3 Exact SHAP agreement is lower because explanation rankings can change under small quantization differences.
- Ranking-margin analysis is useful self-assessment: small rank-3/rank-4 gaps mean the certified ranking is correct for the quantized relation but may be fragile.

#### 7.7 ZK Correctness and Negative Tests

Content:

- Stage 3.4 valid witnesses and Groth16 proofs pass for samples 1-8.
- Negative tests reject malformed public outputs or invalid witness/ranking for samples 1-8.
- Negative-test categories: wrong `y_hat`, wrong top-3, duplicate group ID, out-of-range group ID, malicious `other2_ids`, and private input range violation.
- Explain that proof correctness means consistency with model and private input, not correctness against ground-truth label.

#### 7.8 Circuit Complexity and Proof Cost

Known values:

- Constraints: `8,358`
- Wires: `8,078`
- Private inputs: `106`
- Public inputs: `109`
- R1CS: `1,283,048 bytes`
- zkey: `4,573,072 bytes`
- Stage 3.4 proof evidence over samples 1-8:
  - witness: `58-72 ms`, mean `63 ms`;
  - prove: `1009-1365 ms`, mean `1144 ms`;
  - verify: `618-915 ms`, mean `701 ms`;
  - proof size: `800-807 bytes`, mean `804 bytes`.
- If repeated benchmark numbers are used, label them separately as repeated Stage 3.4 benchmark evidence and do not mix them with `STAGE34_PROOF_REPORT.md`.

Important wording:

> These are local CLI prototype timings, not hardware-independent guarantees.

#### 7.9 Case Studies and Diverse Test Vectors

Known samples:

- Sample 1: TP_attack; top-3: Application, ConnectionState, Protocol.
- Sample 2: TN_normal; top-3: ConnectionState, Protocol, TrafficVolume.
- Sample 3: FN_attack; top-3: Protocol, Application, ConnectionState.
- Sample 4: FP_normal.
- Sample 5: high-confidence attack.
- Sample 6: high-confidence normal.
- Sample 7: borderline score.
- Sample 8: small top-3 margin / near-tie case.

Interpretation:

- FN case shows that proof verifies model computation, not ground-truth correctness.
- FP/FN/borderline/near-tie cases show that the proof harness was tested beyond only clean TP/TN examples.

#### 7.10 Output Leakage and Reference Sensitivity

Known values:

- `y_hat` entropy: `0.4395 bits`
- top-3 sequence entropy: `2.9615 bits`
- 22 / 60 unique ordered sequences
- training_mean is the only verified circuit reference.
- zero_vector and normal_train_mean are offline sensitivity checks only.

Correct claim:

> Input-feature privacy with intentional output disclosure.

#### 7.11 Optional Stage 3.5 Input Commitment Appendix Result

Content:

- Present as appendix-only feasibility evidence.
- Explain what is proved: the private witness opens to the public `input_commitment`.
- Explain what is not proved: full SIEM provenance, raw-log-to-feature preprocessing, ingestion registry trust, replay resistance, or deployment readiness.

Known values:

- Constraints: `25,094`
- Wires: `24,816`
- Public inputs: `110`
- Private inputs: `107`
- Public outputs: `1`
- Constraint overhead versus Stage 3.4: `3.0x`
- Samples: `1`, `7`, and `8`
- Witness: `399-817 ms`, mean `586 ms`
- Prove: `2217-3002 ms`, mean `2730 ms`
- Verify: `690-1647 ms`, mean `1041 ms`
- Tampered public commitment rejected for samples `1`, `7`, and `8`

Recommended wording:

> Stage 3.5 demonstrates that the Stage 3.4 relation can be extended with an input commitment, but full provenance binding remains a deployment-layer problem requiring a trusted ingestion-time commitment registry.

#### 7.12 Summary of Findings

Content:

- Answer RQ1-RQ4 directly.
- Keep concise.

Status:

- To write after Chapter 6.

---

## Chapter 8: Discussion, Limitations, and Conclusion

### Purpose

Interpret findings, state boundaries honestly, and present future work.

### Suggested sections

#### 8.1 Interpretation of Findings

Content:

- Stage 3.4 is the main contribution.
- It upgrades proxy attribution to semantic-group Exact SHAP.
- LR makes Exact SHAP proof feasible through closed form.
- Stage 3.5 is useful as appendix evidence that input commitment binding is technically feasible, but it should not displace Stage 3.4 as the main contribution.

#### 8.2 Strengths of Public-Model/Private-Input Scope

Content:

- Public model is defensible in auditable IDS/SOC settings.
- Verifier may need to know the detector version.
- Sensitive object is network telemetry, not model IP.
- Public model supports reproducibility and model-version checking.

#### 8.3 Limitations

Content:

- Validated only on TON_IoT IDS.
- Public Logistic Regression only.
- LR weaker than XGBoost.
- Exact SHAP verification specialized to public LR and fixed reference.
- No arbitrary-model SHAP.
- No Partition SHAP.
- No sumcheck/GKR.
- No XGBoost-in-ZK.
- Stage 3.5 implements only the circuit-side input-commitment check; full external log provenance is not implemented.
- No raw-log-to-feature proof, ingestion-time registry, replay protection, or production trust model.
- Output leakage exists because `y_hat` and top-3 IDs are public.

#### 8.4 Future Work

Content:

- Full provenance system built around the Stage 3.5 commitment idea, including trusted ingestion registry, metadata schema, replay policy, and raw-log binding.
- Cross-proof consistency using input commitments.
- Hidden-model commitment.
- ZK-friendly models beyond LR.
- Scalable SHAP verification using sumcheck/GKR.
- Evaluation on other tabular domains.
- Deployment-level verifier policy.

#### 8.5 Conclusion

Content:

- Summarize contribution.
- Do not introduce new results.

Status:

- To write near the end.

---

# 8. Current Figure and Table Plan

## Figures already in draft

| Figure | Title | Chapter |
|---|---|---|
| Figure 3.1 | System-level overview of the proposed public-model and private-input framework | Chapter 3 |
| Figure 4.1 | Dataset preparation and baseline modeling pipeline | Chapter 4 |
| Figure 5.1 | Semantic grouping pipeline from processed features to five explanation groups | Chapter 5 |
| Figure 5.2 | Transition from grouped attribution proxy to semantic-group Exact SHAP | Chapter 5 |

## Suggested future figures

| Figure | Purpose | Suggested chapter |
|---|---|---|
| Stage progression figure | Show Stage 3.1 -> 3.4 development | Chapter 6 |
| Constraints by stage | Show circuit cost progression | Chapter 7 |
| Prove/verify time by stage | Show runtime overhead | Chapter 7 |
| Proxy vs Exact SHAP frequency | Show explanation behavior shift | Chapter 7 |
| Top-3 overlap distribution | Show agreement/difference between proxy and Exact SHAP | Chapter 7 |
| Case-study group bars | Optional case-study explanation figure | Chapter 7 or 8 |
| Stage 3.5 commitment flow | Optional appendix figure showing commitment registry requirement | Appendix or Chapter 8 |

Keep main figures limited. Avoid turning the thesis into a generic IDS benchmarking report.

---

# 9. Immediate Formatting and Consistency Tasks

Before continuing too far, fix these in the Word/PDF draft:

1. Remove leftover template chapters after Chapter 5, such as "Writing Style", "Referencing Styles", and "Conclusions" if they are still template content.
2. Ensure all figure captions are below figures.
3. Ensure all table captions are above tables.
4. Use chapter-based numbering consistently: Figure 3.1, Table 3.1, etc.
5. Replace missing or generic references such as "Table summarizes..." with explicit references.
6. Choose one reference style:
   - numeric `[1]`, `[2]`, etc.; or
   - Harvard/name-year.
7. Fix all `TON_IOT` variants to `TON_IoT`.
8. Format mathematical symbols consistently.
9. Keep tables readable; use fewer columns when possible.
10. Do not add proof relation details to Chapters 3-5.

---

# 10. Short Handoff Prompt for Future Chat

Use this prompt when continuing in a new chat:

```text
I am writing a master's thesis titled "Zero-Knowledge Framework for Verifiable Semantic Explanations under Private Input: An Intrusion Detection Case Study." Chapters 3, 4, and 5 are drafted. The thesis is about a public-model/private-input framework, not hidden-model ZK. ZK-XIDS refers only to the IDS case-study implementation, not the general framework. The public model is Logistic Regression; the private input is x_shifted[104]. The verifier intentionally learns y_hat and ordered top-3 semantic group IDs. Exact SHAP values phi_g remain private intermediate values. The main contribution is verifying that prediction and semantic explanation are computed from the same private input under approved public artifacts. Stage 3.5 is only an optional appendix prototype for input commitment; do not present it as full provenance.

Continue from Chapter 6. Do not write Chapter 1 or 2 yet. Keep writing clear, academic, and natural. Avoid overclaiming hidden-model support, arbitrary SHAP, Partition SHAP, sumcheck/GKR, XGBoost-in-ZK, differential privacy, or full SIEM provenance. Use Chapters 3-5 as context: Chapter 3 explains research design and framework overview; Chapter 4 explains dataset, preprocessing, and baselines; Chapter 5 explains raw attribution, semantic grouping, stability/overlap, group-size bias, and transition from attribution proxy to semantic-group Exact SHAP.
```
