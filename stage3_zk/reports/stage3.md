# Stage 3: Zero-Knowledge Privacy-Preserving Intrusion Detection System
## Final Technical Report

**Date**: January 7, 2026  
**Author**: Master's Thesis Research  
**ZK Stack**: Circom 2.x, Groth16, snarkjs 0.7.5
**Feature Count**: **104** (upgraded from 87)

**Reproducible measurements** (timings, constraints, proof/public sizes) are captured by the harness evidence report:
- `stage3_zk/reports/LATEST_REPRO_REPORT.md`

**Scope note:** This is a historical Stage 3.1-3.3 report for the original grouped-attribution prototype. Final thesis claims should be scoped to the public-model/private-input setting and should cite the Stage 3.4 Exact SHAP reports for the final explanation target. The current main claim does not include model-agnostic verification, confidential-model support, differential privacy, or full input provenance binding. Stage 3.5 only provides appendix evidence for a circuit-side input commitment check.

---

## Executive Summary

This report presents the original Stage 3.1-3.3 Zero-Knowledge (ZK) proof prototype for privacy-preserving Intrusion Detection Systems (IDS), implemented in three progressive stages:

1. **Stage 3.1**: Inference-only circuit (baseline)
2. **Stage 3.2**: Semantic group explanation circuit
3. **Stage 3.3**: Top-3 verifiable explanation circuit

**Key Achievement**: Demonstrated verifiable predictions and verifiable top-3 semantic explanations under input-feature privacy with intentional output disclosure. For authoritative, reproducible performance/complexity numbers, refer to `LATEST_REPRO_REPORT.md`.

---

## 1. System Architecture

### 1.1 Threat Model

**Adversarial Assumptions**:
- **Honest-but-curious Verifier**: SOC operator has access to model weights but must not learn client's network traffic patterns
- **Malicious Prover**: Client may attempt to:
  - Forge predictions (claim normal traffic when attack detected)
  - Manipulate explanations (highlight irrelevant features to mislead investigation)
  - Exploit circuit vulnerabilities (constraint solver edge cases)

**Security Goals**:
- **Correctness**: Proof passes only when the prediction is computed correctly from the private witness.
- **Input-feature privacy**: Under the zero-knowledge property, the verifier learns no processed feature values beyond intentional public outputs.
- **Explanation authenticity**: Prover cannot generate a valid proof for an incorrect prediction or claimed top-3 relation without satisfying the circuit.

### 1.2 Model Specification

**Logistic Regression Classifier**:
- **Input features**: 104 (quantized network traffic statistics)
- **Parameters**: 
  - Weights: `w[104]` ∈ [-122130, +122130] (18-bit signed)
  - Bias: `b` ∈ [-68.7B, +68.7B] (36-bit signed)
- **Output**: Binary classification (0 = normal, 1 = attack)
- **Semantic groups**: 5 feature categories
  - Group 1: **Protocol** (3 features)
  - Group 2: **Application** (76 features) 
  - Group 3: **ConnectionState** (13 features)
  - Group 4: **Ports** (2 features)
  - Group 5: **TrafficVolume** (10 features)

---

## 2. Stage 3.1: Inference-Only Circuit (Baseline)

### 2.1 Design

**Circuit**: `inference_only.circom`  
**Purpose**: Prove correct prediction computation without revealing input

**Computation Flow**:
Input: x[104] (private), w[104] (public), b (public)
↓
Constraint 1: Range check x[i] ∈ [-maxAbsX, +maxAbsX]
↓
Constraint 2: Compute contributions c[i] = w[i] × x[i]
↓
Constraint 3: Compute score = Σc[i] + b
↓
Constraint 4: Verify prediction y_hat = 1 if score ≥ 0, else 0
↓
Output: y_hat (public)

**Key Technical Decision - Shifted Inputs**:
```circom
// Problem: Negative values not natively supported in field arithmetic
// Solution: Shift all values to non-negative range
x_shifted[i] = x[i] + maxAbsX  // Now in [0, 2×maxAbsX]
w_shifted[i] = w[i] + maxAbsW  // Now in [0, 2×maxAbsW]
b_shifted = b + B              // Now in [0, 2×B]

// Recover signed values inside circuit
x[i] <== x_shifted[i] - maxAbsX
```

**Bounds Selection**:

| Parameter | Value | Justification |
|-----------|-------|---------------|
| maxAbsX | 297,270,816 | Max quantized feature value from dataset |
| maxAbsW | 122,130 | Max model weight after training |
| B | 2^36 = 68.7B | Upper bound for score range |
| Bc | 2^46 = 70.4T | Bound for intermediate contributions |
| BG | 2^53 = 9.0P | Bound for semantic group sums |

### 2.2 Performance

**Current harness evidence**:
- Latest full evidence report: `stage3_zk/reports/LATEST_REPRO_REPORT.md`
- Constraints: 3,831
- Proof JSON: about 805 bytes
- Public JSON: about 3,509 bytes
- Per-sample prove steps in the latest CLI harness: about 953-1,030ms
- Per-sample verify steps in the latest CLI harness: about 641-733ms

**Circuit Complexity**:
- Constraints: 3,831 in the latest generated R1CS
- Template instances: 104 range checks + 1 score computation

**Analysis**:
- ✅ Smallest circuit among the three stages
- ✅ Verification remains cheaper than proving
- ⚠️ Limited explainability: Only binary prediction revealed

## 3. Stage 3.2: Semantic Group Explanation
### 3.1 Design Evolution
Motivation: Stage 3.1 provides no insight into why a prediction was made. SOC analysts require feature-level explanations for incident investigation.

Circuit: semantic_groups.circom
Extension: Add Block C to compute semantic group contributions

New Computation:

// Block A: Same as Stage 3.1 (inference)
// Block B: Compute absolute contributions a[i] = |w[i] × x[i]|
signal a[n];
signal z[n];  // Sign indicator

for (var i = 0; i < n; i++) {
    c_offset[i] <== c[i] + Bc;
    cSignCheck[i] = LessThan(47);  // Updated bit width for Bc=2^46
    cSignCheck[i].in[0] <== c_offset[i];
    cSignCheck[i].in[1] <== Bc;
    z[i] <== cSignCheck[i].out;  // 1 if negative, 0 if positive
    
    a[i] <== (1 - 2*z[i]) * c[i];  // Absolute value
}

// Block C: Aggregate by semantic groups (private G values)
signal G[5];  // Group contributions (NOT PUBLIC)
for (var g = 0; g < 5; g++) {
    G[g] = Σ(a[i] for i where group_id[i] == g+1)
}
Critical Design Decision: G values remain private signals (internal to circuit), not exposed as public outputs.

Rationale:

Revealing absolute group contributions leaks information about input distribution
Prover computes G internally, uses them for explanation logic, but verifier doesn't see raw values
This preserves zero-knowledge property while enabling downstream explanation

### 3.2 Optimization History
The following numbers are historical Node API / local benchmark notes. For final thesis tables, use `LATEST_REPRO_REPORT.md` and `zk_scaling_benchmark.md`.

Initial Implementation:

Proving time: 822ms (unoptimized)
Contained redundant constraints:
// Redundant: a[i] already bounded by Bc
component aBoundCheck[n] = LessThan(nBitsC);

// Redundant: z[i] construction guarantees binary
z[i] * (z[i] - 1) === 0;
Optimized Implementation:

Proving time: 486ms (initial optimization)
Removed redundant checks (one per feature): 104 bound checks + 104 binary checks
Improvement: -41% proving time
Current harness evidence for Stage 3.2:

- Constraints: 17,684 in the latest generated R1CS
- Proof JSON: about 805 bytes
- Public JSON: about 1,228 bytes
- Per-sample prove steps in the latest CLI harness: about 1,328-1,546ms
- Per-sample verify steps in the latest CLI harness: about 514-531ms

### 3.3 Validation
Test Coverage: 3 samples

Sample 1 (TP): Attack correctly detected (y_pred=1, y_true=1)
Sample 2 (TN): Normal traffic correctly identified (y_pred=0, y_true=0)
Sample 3 (FN): Attack missed by model (y_pred=0, y_true=1)
All samples generated valid proofs, demonstrating circuit robustness across prediction outcomes.

## 4. Stage 3.3: Top-3 Verifiable Explanation
### 4.1 Design Goals
Motivation: Stage 3.2 computes G values privately but doesn't prove which groups are most influential. A malicious prover could:

Claim arbitrary groups as "top-3" without verification
Highlight irrelevant features to mislead SOC investigation
Solution: Extend circuit with cryptographic proof of top-3 authenticity.

### 4.2 Design Decision: Top-3 as Set

Our circuit proves **membership correctness** rather than strict ordering:
- Dominance constraint ensures top-3 groups have larger contributions than other-2
- Ordering constraint (Step 6) provides **canonical representation** when no ties exist
- **In case of ties** (e.g., G[2] == G[3]): Multiple valid orderings exist. 
  Our circuit accepts any ordering satisfying dominance, which is cryptographically 
  sound (the set {g1,g2,g3} is uniquely determined, only permutation varies).

**Thesis Defense**: "For SOC operators, knowing the *set* of top-3 groups is 
sufficient for investigation. Strict ordering within ties provides no additional 
security value, thus we optimize for proving cost."

Circuit: top3_explanation.circom
New Public Inputs:

top3_ids[3]: Claimed top-3 group IDs (e.g., [2, 1, 5] for test sample 1)
New Private Inputs:

other2_ids[2]: Remaining 2 group IDs (e.g., [4, 5])
Verification Constraints (Block D):

Step 1: Range Validation
// All group IDs must be in {1, 2, 3, 4, 5}
template CheckGroupId() {
    signal input id;
    
    component notZero = IsEqual();
    notZero.in[0] <== id;
    notZero.in[1] <== 0;
    notZero.out === 0;  // id ≠ 0
    
    component inRange = LessThan(3);
    inRange.in[0] <== id;
    inRange.in[1] <== 6;
    inRange.out === 1;  // id < 6
}
Step 2: All-Distinct Constraint
// Ensure no duplicate group IDs (10 pairwise checks)
signal all_ids[5] = [top3_ids[0..2], other2_ids[0..1]];

for (var i = 0; i < 5; i++) {
    for (var j = i+1; j < 5; j++) {
        component neq = IsEqual();
        neq.in[0] <== all_ids[i];
        neq.in[1] <== all_ids[j];
        neq.out === 0;  // Must be different
    }
}
Step 3: Permutation Constraint
// Verify {all_ids} is a permutation of {1,2,3,4,5}
sum_ids <== all_ids[0] + ... + all_ids[4];
sum_ids === 15;  // 1+2+3+4+5 = 15

sumsq_ids <== all_ids[0]² + ... + all_ids[4]²;
sumsq_ids === 55;  // 1²+2²+3²+4²+5² = 55
Mathematical Proof of Sufficiency:

Given: sum = 15, sumsq = 55, all_ids ∈ {1..5}
Claim: all_ids is a permutation of {1,2,3,4,5}
Proof: By Cauchy-Schwarz inequality, for any multiset of 5 integers from {1..5}:
sum = 15 ⟹ no element can be 0 or >5 (else sum ≠ 15)
sumsq = 55 ⟹ no duplicates (else sumsq > 55 or sum < 15)
Therefore, {all_ids} = {1,2,3,4,5} (permutation)

Step 4: Group Mapping
// Map group IDs to their G values using onehot selection
template Select5() {
    signal input arr[5];  // G values
    signal input idx;     // Group ID (1..5)
    signal output out;
    
    component eq[5];
    signal onehot[5];
    
    for (var k = 0; k < 5; k++) {
        eq[k] = IsEqual();
        eq[k].in[0] <== idx;
        eq[k].in[1] <== k + 1;
        onehot[k] <== eq[k].out;
    }
    
    // Defensive: ensure exactly one match
    onehot[0] + ... + onehot[4] === 1;
    
    // Accumulator pattern (avoid non-quadratic constraint)
    signal acc[6];
    acc[0] <== 0;
    for (var k = 0; k < 5; k++) {
        acc[k+1] <== acc[k] + onehot[k] * arr[k];
    }
    out <== acc[5];
}

// Apply to all 5 group IDs
signal G_mapped[5];
for (var idx = 0; idx < 5; idx++) {
    sel[idx] = Select5();
    sel[idx].arr <== G;  // Private group values
    sel[idx].idx <== all_ids[idx];
    G_mapped[idx] <== sel[idx].out;
}
**Step 5: Dominance Constraint**
```circom
// Verify top-3 groups dominate other-2 groups
// For all t ∈ {0,1,2}, o ∈ {3,4}: G_mapped[t] ≥ G_mapped[o]

for (var t = 0; t < 3; t++) {
    for (var o = 3; o < 5; o++) {
        component dom = LessThan(54);  // Updated for nBitsG=54
        dom.in[0] <== G_mapped[t];
        dom.in[1] <== G_mapped[o];
        dom.out === 0;  // NOT(G_mapped[t] < G_mapped[o])
    }
}
```
**Constraint Count**: 6 comparisons (3 × 2 cross-product)

**Step 6: Ordering Constraint**
```circom
// Verify deterministic ordering within top-3
// G_mapped[0] ≥ G_mapped[1] ≥ G_mapped[2]

component order01 = LessThan(54);  // Updated for nBitsG=54
order01.in[0] <== G_mapped[0];
order01.in[1] <== G_mapped[1];
order01.out === 0;  // G_mapped[0] ≥ G_mapped[1]

component order12 = LessThan(54);  // Updated for nBitsG=54
order12.in[0] <== G_mapped[1];
order12.in[1] <== G_mapped[2];
order12.out === 0;  // G_mapped[1] ≥ G_mapped[2]
```

**Note on Ties**: Non-strict inequality (≥) allows tied groups. If G[2] == G[3], any ordering satisfying dominance is valid. This is defendable as "deterministic up to equivalence class."

### 4.3 Security Analysis
#### Test 1: Wrong Explanation Attack
Setup: Generate valid input, swap top3_ids[2] with other2_ids[0]

Script: test_wrong_explanation.py
# Craft malicious explanation: swap Group 5 with Group 4
correct_top3 = [2, 1, 5]  # Application, Protocol, TrafficVolume
correct_other2 = [4, 3]   # Ports, ConnectionState

# Malicious prover's claim
fake_top3 = [2, 1, 4]     # Replace TrafficVolume with Ports
fake_other2 = [5, 3]      # Move TrafficVolume to "others"
Result
```text
[INFO] snarkJS: Assert Failed. TraceBack:
top3_explanation.circom:302:12
```

Analysis: Circuit correctly rejected at Line 302: dominance constraint

G[5] (TrafficVolume) = 88.9M > G[4] (Ports) = 58.7M
Dominance check failed: claimed top-3 group Ports does not dominate the moved-out TrafficVolume group.
Conclusion: Adversary cannot forge fake explanation ✅

#### Test 2: Robustness Across Prediction Classes
| Sample | Type | y_true | y_pred | Top-3 Explanation | Proof Status |
|--------|------|--------|--------|------------------|-------------|
| 1 | TP (attack detected) | 1 | 1 | [2, 1, 5] | ✅ Valid |
| 2 | TN (normal traffic) | 0 | 0 | [2, 3, 1] | ✅ Valid |
| 3 | FN (attack missed) | 1 | 0 | [2, 1, 5] | ✅ Valid |
Observations:

#### Test 3: Malicious Witness Attack

**Attack Vector**: Adversarial prover keeps `top3_ids` correct (to pass dominance) but provides manipulated `other2_ids` to exploit constraint gaps.

**Hypothesis**: If all-distinct and permutation constraints are incomplete, prover could:
- Provide duplicate IDs in `other2_ids` (e.g., `[4, 4]`)
- Reuse a top3 group in `other2_ids` (e.g., `[4, 2]`)
- Inject out-of-range IDs (e.g., `[6, 4]`)

**Test Setup**:
- Correct explanation for sample 1: `top3 = [2, 1, 5]`, `other2 = [4, 3]`
- Malicious inputs crafted to test each attack vector

**Results**:

| Attack Scenario | Malicious other2 | Failed At | Status |
|-----------------|------------------|-----------|---------|
| **Duplicate witness** | `[4, 4]` | Line 248 (all-distinct) | ✅ Rejected |
| **Permutation violation** | `[4, 2]` | Line 248 (all-distinct) | ✅ Rejected |
| **Out-of-range ID** | `[6, 4]` | Line 53 (CheckGroupId) | ✅ Rejected |

**Analysis**:

1. **All-distinct constraint** (Lines 246-258): 10 pairwise `IsEqual` checks catch both duplicate and permutation violations before sum/sumsq constraints even execute.

2. **CheckGroupId template** (Lines 38-53): Range checks (`id != 0` and `id < 6`) prevent injection of invalid group IDs, failing at witness generation.

3. **Defense-in-depth validation**: Multiple overlapping constraints ensure no single constraint failure leads to security breach.

**Security Implication**:

Circuit successfully defends against **malicious witness manipulation**, proving that:
- ✅ Prover cannot bypass dominance checks by faking private `other2_ids`
- ✅ All-distinct constraint is **cryptographically enforced**, not just arithmetically
- ✅ Permutation constraints (`sum=15`, `sumsq=55`) provide redundant validation

**Contrast with unverified systems**: In traditional ML explainability (LIME, SHAP), client could claim arbitrary feature importance without verification. Our ZK-XAI system provides **cryptographic proof** that explanations match actual model computation.

Explanation diversity: sample 1 and sample 3 use [2, 1, 5] (Application, Protocol, TrafficVolume), while sample 2 uses [2, 3, 1] (Application, ConnectionState, Protocol).
Prediction independence: Circuit accepts both y_pred=0 and y_pred=1 when the explanation matches the computed group ranking.
Implication: Explanation reflects feature importance for the private input, not just the prediction outcome.

### 4.4 Performance
Current harness evidence:

- Latest full evidence report: `stage3_zk/reports/LATEST_REPRO_REPORT.md`
- Constraints: 18,719
- Proof JSON: about 803 bytes
- Public JSON: about 1,178 bytes
- Per-sample prove steps in the latest CLI harness: about 1,266-1,468ms
- Per-sample verify steps in the latest CLI harness: about 531-608ms
- Repeated Stage 3.3 benchmark (`zk_scaling_benchmark.md`): prove mean 1,532ms, p50 1,484ms, p95 1,847ms; verify mean 588ms, p50 562ms, p95 696ms

Historical constraint breakdown estimate:

| Block | Constraints | Description |
|-------|-------------|-------------|
| A+B+C | ~17,684 measured constraints | Inherited from Stage 3.2 |
| Range checks | 5 × 10 = 50 | CheckGroupId templates |
| All-distinct | 10 × 30 = 300 | IsEqual components |
| Permutation | 2 | sum=15, sumsq=55 |
| Select5 mapping | 5 × 50 = 250 | Onehot selection |
| Bound checks | 5 × 120 = 600 | G_mapped range validation (54-bit) |
| Dominance | 6 × 120 = 720 | LessThan(54-bit) |
| Ordering | 2 × 120 = 240 | LessThan(54-bit) |
| **Total** | **18,719 measured constraints** | Latest R1CS |
## 5. Comparative Analysis
### 5.1 Performance Summary
| Stage | Constraints | Latest prove-step range | Latest verify-step range | Notes |
|---|---:|---:|---:|---|
| 3.1 (Inference) | 3,831 | 953-1,030ms | 641-733ms | Baseline privacy proof |
| 3.2 (Groups) | 17,684 | 1,328-1,546ms | 514-531ms | Adds private semantic aggregation |
| 3.3 (Top-3) | 18,719 | 1,266-1,468ms | 531-608ms | Adds verifiable top-3 explanation |
Key Metrics:

The current table reports CLI-harness wall-clock steps and includes process overhead. Older Node API numbers are useful as historical optimization notes, but final thesis tables should use one protocol consistently.
5.2 Security-Performance Trade-off
Thesis Defense Narrative:

"The proving overhead from Stage 3.3 purchases three critical security guarantees: (1) input privacy via ZK property, (2) semantic group isolation via absolute value computation, and (3) explanation authenticity via dominance constraints. This represents an acceptable cost for trustworthy AI in security-critical SOC environments."

Quantitative Justification:

Alternative 1 (No ZK): Proving = 0ms, but input-feature privacy is lost if the client must reveal processed traffic features.
Alternative 2 (Stage 3.1 only): proves inference, but no explainability (SOC cannot investigate)
Alternative 3 (Unverified explanation): computes groups, but adversary can mislead (fake top-3)
Our Solution (Stage 3.3): input-feature privacy + prediction authenticity + verifiable explanation authenticity
Cost-benefit: extra constraints buy cryptographic proof that the explanation matches the model computation

### 5.3 Trust vs Speed Design Philosophy
Optimization Opportunities Declined:

Remove gmBoundCheck (Lines 289-296)

Potential saving: ~60ms
Decision: KEPT for defense-in-depth
Rationale: Even though G values are bounded at computation, re-checking G_mapped ensures no circuit bugs in Select5 template
Remove pairwise distinct checks (Lines 246-258)

Potential saving: ~25ms
Decision: KEPT for explicit security
Rationale: Mathematical redundancy (sum+sumsq sufficient) vs explicit security (prover cannot exploit edge cases)
Use LessThan(34) instead of (51)

Potential saving: ~50ms
Decision: KEPT for generalizability
Rationale: Conservative bitwidth future-proofs for model retraining with larger weights
Total potential speedup: ~135ms (20% improvement)

Thesis Position: "We prioritize formal correctness over performance optimization. The incremental 135ms cost ensures defense against potential constraint solver exploits and keeps the circuit robust within the selected public Logistic Regression artifact family."

## 6. Implementation Details
### 6.1 Constraint Optimization Techniques
Technique 1: Accumulator Pattern (Avoid Non-Quadratic Constraints)
// ❌ WRONG: Non-quadratic (more than 2 multiplications)
out <== onehot[0]*arr[0] + onehot[1]*arr[1] + ... + onehot[4]*arr[4];

// ✅ CORRECT: Accumulator (each step has ≤2 muls)
signal acc[6];
acc[0] <== 0;
acc[1] <== acc[0] + onehot[0] * arr[0];  // 1 mul
acc[2] <== acc[1] + onehot[1] * arr[1];  // 1 mul
...
out <== acc[5];
Lesson: Circom's R1CS compiler requires all constraints to be quadratic (max 2 signal multiplications per constraint). Multi-term products must be split into intermediate signals.

Technique 2: Onehot Encoding for Selection
// Problem: Dynamic array indexing not supported in Circom
// arr[idx] ❌ NOT ALLOWED

// Solution: Onehot encoding
onehot[k] = (idx == k+1) ? 1 : 0  // Via IsEqual
out = Σ(onehot[k] × arr[k])       // Only one term active
Application: Select5 template for group ID → G value mapping

Technique 3: Shifted-Input Encoding
// Problem: Field arithmetic treats all values as positive
// Example: -100 represented as p-100 (where p ≈ 2^254)
// Comparisons fail: LessThan(-100, 50) evaluates as LessThan(p-100, 50) ⟹ False

// Solution: Shift to non-negative range
x_shifted = x + maxAbsX
// Now x ∈ [-maxAbsX, maxAbsX] maps to x_shifted ∈ [0, 2×maxAbsX]
// Range check: x_shifted < 2×maxAbsX + 1 ✅

// Recover signed value inside circuit
x <== x_shifted - maxAbsX
Critical Insight: All range checks must be performed on shifted values before recovery

### 6.2 Build Pipeline
Toolchain:

Circom 2.x: Circuit compiler (WSL `circom` on PATH)
Powers of Tau: ptau 15 (~36MB, supports up to 2^15 = 32K constraints)
snarkjs 0.7.5: Groth16 prover/verifier (Windows Node.js)
Workflow:

# 1. Compile circuit
wsl bash -c "circom top3_explanation.circom --r1cs --wasm --sym"

# 2. Groth16 setup (2-3 minutes)
snarkjs groth16 setup top3_explanation.r1cs powersOfTau.ptau circuit.zkey

# 3. Generate proof (current Stage 3.3 CLI harness p50 ~1.48s)
snarkjs groth16 prove circuit.zkey witness.wtns proof.json public.json

# 4. Verify proof (current Stage 3.3 CLI harness p50 ~0.56s)
snarkjs groth16 verify verification_key.json public.json proof.json

### 6.3 Input Preparation
Script: 01_prepare_input_stage33.py
# 1. Compute semantic groups (private)
G = [0] * 5
for i in range(104):
    g = group_id[i] - 1  # Convert to 0-indexed
    G[g] += abs(w[i] * x[i])

# 2. Extract top-3 by sorting
sorted_indices = np.argsort(G)[::-1]  # Descending order
top3_ids = [sorted_indices[0]+1, sorted_indices[1]+1, sorted_indices[2]+1]
other2_ids = [sorted_indices[3]+1, sorted_indices[4]+1]

# 3. Generate circuit input
circuit_input = {
    "x_shifted": (x + maxAbsX).tolist(),
    "w_shifted": (w + maxAbsW).tolist(),
    "b_shifted": int(b + B),
    "y_hat": int(y_pred),
    "top3_ids": top3_ids,      # Public
    "other2_ids": other2_ids   # Private
}
Output: input_stage33_sample_X.json (fed to snarkjs witness calculator)

## 7. Validation & Testing

### 7.1 Functional Testing
Test Suite:

✅ Positive test: Valid input → proof generation succeeds
✅ Wrong explanation test: Swapped top-3 → proof generation fails (Assert Failed at dominance constraint)
✅ Robustness test: 3 samples (TP, TN, FN) → all proofs verify
Validation Script: validate_stage33.py

# Recompute expected top-3 from test vector
G_expected = compute_semantic_groups(x, w, group_id)
top3_expected = np.argsort(G_expected)[::-1][:3] + 1

# Compare with public input
top3_actual = json.load("public_stage33_sample_X.json")[-3:]
assert np.array_equal(top3_actual, top3_expected)
Result: All samples validated ✅

### 7.1.2 Explanation Diversity Analysis

To validate that top-3 explanations reflect genuine input sensitivity 
(rather than circuit artifacts), we analyzed 50 test samples (25 attack, 25 normal).

**Findings**:

1. **Pattern Diversity**: 
   - 3 unique patterns in attack class (12% diversity rate)
   - 4 unique patterns in normal class (16% diversity rate)
   - **Conclusion**: Explanations vary with input, not fixed ✅

2. **Top-1 Group Consistency**:
   - Group 2 (Application) dominates 100% of samples in both classes
   - Reflects dataset composition: 74/104 features are application-layer
   - Validates semantic grouping captures domain structure

3. **Class-Specific Patterns**:
   - **TrafficVolume (Group 5)** appears in 12% normal samples, 0% attacks
   - **Ports (Group 4)** in top-3 for 24% attacks vs 8% normal
   - Average TrafficVolume contribution: 382M (normal) vs 93M (attack) → **4× difference**

4. **Jaccard Similarity**: 0.75 (high overlap)
   - Interpretation: Attack/normal share top-3 membership but differ in **ordering and magnitudes**
   - Validates model learned subtle decision boundaries (not trivial separation)


### 7.2 Performance Testing
Benchmark Script: benchmark_stage33.js
const { performance } = require('perf_hooks');

// Warm-up: 10 runs
for (let i = 0; i < 10; i++) {
    await snarkjs.groth16.prove(zkeyPath, witnessPath);
}

// Benchmark: 100 runs
let times = [];
for (let i = 0; i < 100; i++) {
    const start = performance.now();
    await snarkjs.groth16.prove(zkeyPath, witnessPath);
    times.push(performance.now() - start);
}

console.log(`Mean: ${mean(times).toFixed(2)}ms`);
console.log(`Median: ${median(times)}ms`);
Metrics Collected:

Mean, median, min, max, standard deviation
Separate measurements for proving and verification

**Table 7.2: Top-3 Pattern Frequency**

| Pattern | Attack (%) | Normal (%) | Interpretation |
|---------|-----------|-----------|----------------|
| (2,3,1) | 56.0 | 40.0 | Application-heavy traffic |
| (2,1,3) | 20.0 | 40.0 | Protocol-first variant |
| (2,1,4) | 24.0 | 8.0 | Port-focused (scan activity) |
| (2,5,1) | 0.0 | 12.0 | Volume-heavy normal traffic |

**Thesis Implication**: Our ZK-XAI system successfully captures **input-dependent explanations** 
while maintaining cryptographic verification. The observed pattern diversity (3-4 unique) 
validates that the circuit does not trivially output fixed values.

## 8. Deployment Considerations
### 8.1 SOC Integration
┌─────────────┐                  ┌─────────────┐
│   Client    │                  │  SOC Server │
│  (Prover)   │                  │ (Verifier)  │
├─────────────┤                  ├─────────────┤
│ 1. Capture  │                  │ 5. Verify   │
│    traffic  │                  │    proof    │
│             │                  │ latest bench│
│ 2. Quantize │                  │             │
│    features │                  │ 6. Extract  │
│             │                  │    top-3    │
│ 3. Generate │  ──(proof)──>    │    from     │
│    proof    │                  │    public   │
│ latest bench│                  │    input    │
│             │                  │             │
│ 4. Send     │                  │ 7. Alert if │
│    proof +  │                  │    y_hat=1  │
│    public   │                  │             │
└─────────────┘                  └─────────────┘
Bandwidth:

Proof size: ~1KB (Groth16 fixed size)
Public input: ~1.2KB for Stage 3.3 sample 1 in the latest report
Total per inference: about 2KB proof + public JSON, excluding transport metadata
Throughput:

Prover: roughly 0.6-0.8 Stage 3.3 proofs/sec under current CLI-harness timing
Verifier: cheaper than proving; current CLI-harness verify p50 is about 562ms for Stage 3.3
Bottleneck: Prover-side proving time
### 8.2 Scalability Analysis
Scenario: SOC monitoring 1000 clients

Option 1 - Sequential Processing:

Total proving time: approximately 1000 × 1.5s = 1500 seconds (~25 minutes) under current CLI-harness timing
Not suitable for real-time monitoring
Option 2 - Parallel Processing:

Deploy 100 prover workers (multi-core or distributed)
Per-worker load: 10 clients
Total time: approximately 10 × 1.5s = 15 seconds under current CLI-harness timing
Acceptable for periodic batch processing
Option 3 - Hardware Acceleration:

Use GPU-accelerated ZK provers (e.g., rapidsnark)
Estimated speedup: 5-10× could move proving toward a few hundred milliseconds
Future work: Benchmark with GPU backend
### 8.3 Trusted Setup
Powers of Tau Ceremony:

Current: Using pre-existing ptau 15 from Hermez ceremony
Security: Relies on at least 1 honest participant in multi-party computation (MPC)
Transparency: ptau 15 hash published and verified by community
Circuit-Specific Setup:

Current: Single-party zkey generation (development only)
Production: Must perform MPC ceremony for circuit.zkey
Tool: snarkjs zkey contribute (multi-round protocol)
Recommendation: For thesis, document that production deployment requires MPC; current single-party setup sufficient for proof-of-concept.

## 9. Thesis Contributions
### 9.1 Novel Aspects
Shifted-Input Encoding for Signed Arithmetic

Implemented shifted-input encoding for signed fixed-point arithmetic in the LR inference circuits.
The idea may be reusable in other bounded fixed-point circuits, but the implemented thesis claim is limited to the public Logistic Regression IDS model and compatible public linear/logistic tabular models.
Semantic Group Privacy

System design: compute group contributions as private signals and use them only for internal verification.
This avoids publishing group magnitudes; the public leakage is limited to the prediction and top-3 group IDs.
Verifiable Top-K Explanation

A ZK circuit for cryptographic proof of semantic-group top-k explanation authenticity.
Defense against explanation manipulation attacks in the selected public-model/private-input IDS setting.
### 9.2 Comparison with Related Work

| Work | ZK System | Explainability | Input Privacy | Explanation Authenticity |
|------|-----------|----------------|---------------|-------------------------|
| zkCNN (EZKL) | Halo2 | ❌ No | ✅ Yes | N/A |
| ZKCSP | Groth16 | ✅ Feature-level | ⚠️ Partial | ❌ Unverified |
| **Ours (Stage 3.3)** | **Groth16** | **Top-3 groups** | **Input-feature privacy with public outputs** | **Cryptographic proof** |
### 9.3 Limitations & Future Work

**Limitations**:
- Model-specific: Circuit hardcoded for 104 features, 5 groups
- Linear models only: Extension to neural networks requires polynomial constraints
- Prover cost: current Stage 3.3 CLI-harness p50 prove time is about 1.48s, which may be too slow for edge devices

**Future Directions**:

Recursive SNARKs: Amortize proving cost across multiple inferences
Hardware acceleration: GPU-based provers for lower-latency proving
Dynamic circuits: Support variable feature counts without recompilation
Neural network support: Polynomial approximations for ReLU activations
## 10. Conclusion
This work demonstrates that Zero-Knowledge proofs can provide trustworthy AI explanations without compromising input privacy, achieving a practical balance between security, explainability, and performance.

Key Results:

✅ Reproducible Stage 3.3 proving evidence: p50 prove about 1.48s in current CLI harness
✅ Reproducible Stage 3.3 verification evidence: p50 verify about 0.56s in current CLI harness
✅ Cryptographic explanation authenticity: Adversary cannot forge fake top-3
Input-feature privacy up to intentional output disclosure: verifier learns the prediction and top-3 group IDs, but not the processed feature vector or private group magnitudes.
Thesis Position: "The additional overhead over inference-only ZK is an acceptable cost for verifiable explainability in security-critical domains. We prioritize trust over speed, employing defense-in-depth constraint design to ensure formal correctness."
stage3_zk/
├── circuits/
│   ├── inference_only/           # Stage 3.1
│   │   ├── inference_only.circom
│   │   └── build/
│   ├── semantic_groups/          # Stage 3.2
│   │   ├── semantic_groups.circom
│   │   ├── powersOfTau28_hez_final_15.ptau
│   │   └── build/
│   └── top3_explanation/         # Stage 3.3
│       ├── top3_explanation.circom
│       └── build/
├── scripts/
│   ├── 01_prepare_input_stage33.py
│   ├── 02_build_circuit_stage33.ps1
│   ├── 03_generate_proof_stage33.sh
│   ├── 04_verify_proof_stage33.sh
│   ├── test_wrong_explanation.py
│   ├── validate_stage33.py
│   └── benchmark_stage33.js
├── test_vectors/
│   ├── test_sample_1.json        # TP (attack detected)
│   ├── test_sample_2.json        # TN (normal traffic)
│   └── test_sample_3.json        # FN (attack missed)
├── outputs/
│   └── proofs/
│       ├── proof_stage33_sample_1.json
│       ├── public_stage33_sample_1.json
│       ├── benchmark_stage33.json
│       └── benchmark_stage32.json
└── reports/
    ├── stage3.md                 # This technical report
    └── FINAL_SUMMARY.md          # Narrative final summary
## Appendix B: Test Results

### Sample 1 (TP - Attack Detected)

**Input**: sample_id=0, label="TP_attack", y_true=1, y_pred=1

**Top-3**: [2, 1, 5] = Application → Protocol → TrafficVolume

**Group Contributions**:
| Group | Contribution | Normalized |
|-------|--------------|------------|
| Application | 2,404,909,056 | 2.4B |
| Protocol | 765,722,624 | 766M |
| TrafficVolume | 88,863,615 | 89M |
| Ports | 58,746,793 | 59M |
| ConnectionState | 57,540,608 | 58M |

**Proof**: ✅ Generated successfully  
**Verification**: ✅ Passed
### Sample 2 (TN - Normal Traffic)

**Input**: sample_id=1, label="TN_normal", y_true=0, y_pred=0

**Top-3**: [2, 3, 1] = Application → ConnectionState → Protocol

**Proof**: ✅ Generated successfully  
**Verification**: ✅ Passed
### Sample 3 (FN - Attack Missed)

**Input**: sample_id=43, label="FN_attack", y_true=1, y_pred=0

**Top-3**: [2, 1, 5] = Application → Protocol → TrafficVolume

**Proof**: ✅ Generated successfully  
**Verification**: ✅ Passed
### Wrong Explanation Test

**Manipulation**: Swap top3[2] (Group 1) with other2[0] (Group 4)

**Result**: ❌ Assert Failed at line 302 (dominance constraint)

**Interpretation**: Circuit correctly rejects fake explanation
## Appendix C: Current Benchmark Pointers

The current authoritative benchmark artifacts are generated by the reproducibility harness:

- `stage3_zk/reports/LATEST_REPRO_REPORT.md`
- `stage3_zk/reports/zk_scaling_benchmark.md`

Latest complexity table:

| Stage | Constraints | Wires | Public Inputs | Private Inputs | Proof bytes | Public bytes |
|---:|---:|---:|---:|---:|---:|---:|
| 31 | 3,831 | 3,829 | 106 | 104 | 805 | 3,509 |
| 32 | 17,684 | 17,150 | 111 | 104 | 805 | 1,228 |
| 33 | 18,719 | 18,043 | 109 | 106 | 803 | 1,178 |

Latest repeated Stage 3.3 benchmark:

| Step | Mean ms | p50 ms | p95 ms |
|---|---:|---:|---:|
| prepare_input | 77 | 70 | 109 |
| witness_smoke | 87 | 78 | 150 |
| prove | 1,532 | 1,484 | 1,847 |
| verify | 588 | 562 | 696 |

End of Report

Document Metadata:

Version: 1.0 (Final)
Last Updated: January 7, 2026
Total Pages: 18
Word Count: ~6,800
