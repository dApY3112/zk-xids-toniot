# Stage 3: Zero-Knowledge Explainable IDS — Technical Notes

## Overview
This stage implements a privacy-preserving explainability layer using zero-knowledge proofs (ZK-SNARKs). The system proves correct inference + semantic group ranking without revealing raw network traffic features.

---

## 1. Frozen Parameters (from Stage 1 & 2)

### Feature Vector
- **n = 87 features** (frozen from preprocessing pipeline)
- Feature order: `artifacts/feature_order.json`
- Feature schema:
  - 12 numeric features (duration, bytes, packets, ports)
  - 9 categorical features (one-hot encoded → 75 features)
  - 5 boolean features (DNS/SSL flags)

### Model (Logistic Regression)
- Weights: **w ∈ ℝ^87**
- Bias: **b ∈ ℝ**
- Decision rule: `y_hat = 1 if score >= 0 else 0`, where `score = Σ(w[i] * x[i]) + b`

### Semantic Groups (5 groups)
1. **Protocol** (group_id=1): `proto_icmp`, `proto_tcp`, `proto_udp`
2. **Application** (group_id=2): `service_*`, `http_*`, `ssl_*`, `dns_*`, `weird_*`
3. **ConnectionState** (group_id=3): `conn_state_*` (REJ, SF, S0, etc.)
4. **Ports** (group_id=4): `src_port`, `dst_port`
5. **TrafficVolume** (group_id=5): `*_bytes`, `*_pkts`, `duration`, etc.

Mapping: `artifacts/group_map.json`

---

## 2. Quantization Scheme (Fixed-Point Arithmetic)

To support ZK circuits (which operate on finite fields), we quantize all floats to integers:

### Scales
- **Sx = 2^16 = 65,536** (input quantization)
- **Sw = 2^12 = 4,096** (weight quantization)

### Quantization
x_int[i] = round(x[i] * Sx)
w_int[i] = round(w[i] * Sw)
b_int = round(b * Sx * Sw)

### Score Computation (Integer)
score_int = Σ(x_int[i] * w_int[i]) + b_int
y_hat = (score_int >= 0) ? 1 : 0

**Note:** The scales `Sx` and `Sw` are public constants embedded in the circuit.

---

## 3. Bounds (for ZK Field Constraints)

From test set analysis (`artifacts/bounds.json`):

- **max(|x_int|)**: 67,995,696 (~26 bits)
- **max(|w_int|)**: 68,314 (~17 bits)
- **max(|score_int|)**: 33,683,198,924 (~35 bits)

These bounds must fit within the ZK field (typically ~254 bits for BN254 curve, common in zkSNARKs).

**Verification:** All bounds < 2^36 (safe margin of 218 bits for 254-bit field).

### Bit Budget Analysis
Field size (BN254): 254 bits
Max score: 35 bits
Max intermediate: 43 bits (x_int * w_int per feature)
Safety margin: 211 bits ✅

---

## 4. Circuit Levels (Progressive Complexity)

### Level 1: Inference Only
**Goal:** Prove `y_hat` is computed correctly from private `x` and public `w, b`.

**Public Inputs:**
- `w_int[87]`, `b_int` (model parameters)
- `Sx`, `Sw` (scales)
- `y_hat` (predicted label: 0 or 1)

**Private Witness:**
- `x_int[87]` (quantized feature vector)

**Constraints:**
score = Σ(w_int[i] * x_int[i]) + b_int // 87 multiplications + 86 additions
y_hat == (score >= 0) // sign check

**Challenge:** Implementing `>=` comparison in ZK (use range proofs or bit decomposition).

**Estimated Complexity:**
- Constraints: ~500-1000 (depends on comparison gadget)
- Proof size: ~200-300 bytes (Groth16)
- Proving time: ~0.5-2 seconds (CPU)

---

### Level 2: Inference + Group Aggregation
**Goal:** Prove `y_hat` + compute semantic group contributions `G[1..5]`.

**Additional Public Inputs:**
- (optional) `G[1..5]` — group contribution sums

**Additional Constraints:**

**Challenge:** Implementing `>=` comparison in ZK (use range proofs or bit decomposition).

**Estimated Complexity:**
- Constraints: ~500-1000 (depends on comparison gadget)
- Proof size: ~200-300 bytes (Groth16)
- Proving time: ~0.5-2 seconds (CPU)

---

### Level 2: Inference + Group Aggregation
**Goal:** Prove `y_hat` + compute semantic group contributions `G[1..5]`.

**Additional Public Inputs:**
- (optional) `G[1..5]` — group contribution sums

**Additional Constraints:**
For each i in [0..86]:
c[i] = w_int[i] * x_int[i] // contribution per feature
abs_c[i] = |c[i]| // absolute value
gid = group_id[i] // constant from group_map.json
G[gid] += abs_c[i] // accumulate by group

**Challenge:** Implementing `abs()` in ZK:
- Introduce sign bit `z ∈ {0,1}`
- Enforce: `abs_c = (1 - 2z) * c` and `abs_c >= 0`

**Estimated Complexity:**
- Constraints: ~2000-3000 (adds ~87 abs() gadgets)
- Proof size: ~250-350 bytes
- Proving time: ~2-5 seconds

---

### Level 3: Full Top-3 Explainability (Option A)
**Goal:** Prove the 3 groups with highest contributions are `(g1, g2, g3)`.

**Public Inputs:**
- `w_int`, `b_int`, `y_hat` (from Level 1)
- `top3_groups = (g1, g2, g3)` where each `g ∈ {1,2,3,4,5}`

**Private Witness:**
- `x_int[87]`
- `g4, g5` (the 2 remaining groups, private)

**Constraints:**

1. **Permutation check** (ensure `{g1, g2, g3, g4, g5}` is a permutation of `{1,2,3,4,5}`):
allDistinct(g1, g2, g3, g4, g5) // pairwise inequality
sum(g1..g5) = 15 // 1+2+3+4+5 = 15
sumSquares(g1..g5) = 55 // 1²+2²+3²+4²+5² = 55

2. **Top-3 constraint**:
For each t in {g1, g2, g3}:
G[t] >= G[g4] // top-3 beats g4
G[t] >= G[g5] // top-3 beats g5


3. **(Optional) Ordering**:
G[g1] >= G[g2] >= G[g3] // enforce descending order


**Why this works:** With only 5 groups, permutation check is lightweight (no need for complex sorting networks).

**Estimated Complexity:**
- Constraints: ~3000-4000 (adds ~20 comparisons + permutation check)
- Proof size: ~300-400 bytes
- Proving time: ~5-10 seconds

---

## 5. Crypto Implementation Notes

### 5.1. Absolute Value in ZK
Witness: z ∈ {0,1}
Constraints:
z * (1 - z) = 0 // z is boolean
abs_c = (1 - 2z) * c // if z=0 => abs_c=c, if z=1 => abs_c=-c
abs_c >= 0 // range constraint (or implicit from usage)

### 5.2. Comparison (>=) in ZK
To prove a >= b:
diff = a - b
Prove: diff is non-negative (use bit decomposition or range proof)


Most ZK libraries (Circom, Noir, gnark) provide `LessThan` or `GreaterEqThan` gadgets.

### 5.3. Permutation Check (for 5 groups)
Constraints:
g1, g2, g3, g4, g5 ∈ {1,2,3,4,5} // range checks
allDistinct(g1..g5) // 10 pairwise inequality checks
sum = 15 (since 1+2+3+4+5=15)
sum_sq = 55 (since 1²+2²+3²+4²+5²=55)


These 3 conditions + distinctness guarantee permutation.

---

## 6. Benchmark Plan

Measure performance for each circuit level:

| Circuit Level          | Proof Gen (ms) | Verify (ms) | Proof Size (KB) | Notes |
|------------------------|----------------|-------------|-----------------|-------|
| Inference Only         | TBD            | TBD         | TBD             | Baseline |
| + Group Aggregation    | TBD            | TBD         | TBD             | +abs() overhead |
| + Top-3 Constraint     | TBD            | TBD         | TBD             | Full explainability |

**Test hardware:** [TO BE FILLED: CPU model, RAM, GPU if used]

**Measurement method:**
- Average over 100 proofs per level
- Use test vectors from `test_vectors/` (TP, TN, FN samples)
- Measure:
  - Proof generation time (prover computation)
  - Verification time (verifier computation)
  - Proof size (bytes on disk/network)

---

## 7. Security Assumptions

1. **Soundness:** Malicious prover cannot forge a valid proof for incorrect `y_hat` or `top3_groups` without breaking the underlying zkSNARK security (computational assumption).

2. **Zero-Knowledge:** Verifier learns nothing about private `x_int` except what's revealed by public outputs (`y_hat`, `top3_groups`). The proof itself leaks no information about the feature values.

3. **Trusted Setup (Groth16 only):**
   - If using Groth16 zkSNARK, requires a one-time trusted setup ceremony.
   - Alternative: Use PLONK/Marlin for universal setup (no circuit-specific trusted setup).

4. **Field Arithmetic:** All computations are modulo a large prime (BN254 field ~254 bits). Integer overflow is prevented by bound checks.

---

## 8. Limitations & Future Work

### Current Limitations
- **Quantization error:** Fixed-point arithmetic introduces small rounding errors. Impact measured in Stage 1: <0.1% accuracy difference vs. float model.
- **Field overflow:** Bounds must be carefully checked to ensure no overflow in 254-bit field. Current bounds are safe (35 bits max).
- **Proof size:** Current zkSNARKs (Groth16) produce ~200-500 byte proofs. Acceptable for IDS deployment over network.
- **Proving time:** 5-10 seconds per proof (CPU-only). Acceptable for offline audit or batch processing. Real-time detection still uses plaintext model.

### Future Directions
1. **Multi-class classification:** Extend to detect specific attack types (not just binary).
2. **Tree-based models:** Implement XGBoost inference in ZK using decision tree gadgets.
3. **Hardware acceleration:** Use GPU/FPGA for faster proof generation.
4. **Recursive proofs:** Batch multiple inferences into one proof for efficiency.
5. **Dynamic top-k:** Allow verifier to request top-k for any k ∈ {1..5} without re-proving.

---

## 9. Reproducibility

All artifacts frozen in `artifacts/`:
- **feature_order.json** — 87 features in fixed order
- **group_map.json** — 5 semantic groups (Protocol, Application, ConnectionState, Ports, TrafficVolume)
- **model_public.json** — quantized weights (w_int[87], b_int, scales)
- **bounds.json** — field constraints (max values for safe arithmetic)

Test vectors in `test_vectors/` for circuit validation:
- **test_sample_1.json** — True Positive attack (correctly detected)
- **test_sample_2.json** — True Negative normal traffic
- **test_sample_3.json** — False Negative attack (missed, for analysis)

---

## 10. Implementation Roadmap

### Phase 1: Circuit Development (Week 1-2)
- [ ] Implement Level 1 (inference only) in Circom/Noir
- [ ] Test with `test_sample_1.json`
- [ ] Verify proof generation and verification work

### Phase 2: Group Aggregation (Week 3)
- [ ] Add abs() gadget for contribution computation
- [ ] Implement group accumulation logic
- [ ] Test with all 3 test vectors

### Phase 3: Top-3 Constraint (Week 4)
- [ ] Implement permutation check
- [ ] Add top-3 comparison constraints
- [ ] End-to-end test

### Phase 4: Benchmarking (Week 5)
- [ ] Run 100 proofs per level
- [ ] Collect timing and size metrics
- [ ] Fill in benchmark table (Section 6)

### Phase 5: Thesis Writing (Week 6+)
- [ ] Document results
- [ ] Compare with related work
- [ ] Discuss limitations and future work

---

**Last Updated:** December 28, 2025  
**Pipeline Version:** Stage 1 (processed_subset_3, 3M samples) → Stage 2 (k=5 explainability) → Stage 3 (ZK circuits)  
**Status:** Artifacts ready ✅ | Circuits pending implementation