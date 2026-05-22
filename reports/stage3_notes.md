# Stage 3: Zero-Knowledge Explainable IDS — Technical Notes

## Overview
This stage implements a privacy-preserving explainability layer using zero-knowledge proofs (ZK-SNARKs). The system proves correct inference + semantic group ranking without revealing raw network traffic features.

---

## 1. Frozen Parameters (from Stage 1 & 2)

### Feature Vector
- **n = 104 features** (frozen from preprocessing pipeline)
- Feature order: `stage3_zk/artifacts/feature_order.json`
- Feature schema:
  - 12 numeric features (duration, bytes, packets, ports)
  - 9 categorical features (one-hot encoded → 87 features)
  - 5 boolean features (DNS/SSL flags)

### Model (Logistic Regression)
- Weights: **w ∈ ℝ^104**
- Bias: **b ∈ ℝ**
- Decision rule: `y_hat = 1 if score >= 0 else 0`, where `score = Σ(w[i] * x[i]) + b`

### Semantic Groups (5 groups)
1. **Protocol** (group_id=1, 3 features): `proto_icmp`, `proto_tcp`, `proto_udp`
2. **Application** (group_id=2, 76 features): `service_*`, `http_*`, `ssl_*`, `dns_*`, `weird_*`
3. **ConnectionState** (group_id=3, 13 features): `conn_state_*` (REJ, SF, S0, etc.)
4. **Ports** (group_id=4, 2 features): `src_port`, `dst_port`
5. **TrafficVolume** (group_id=5, 10 features): `*_bytes`, `*_pkts`, `duration`, etc.

Mapping: `stage3_zk/artifacts/group_map.json`

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

### Signed values inside ZK circuits (implementation detail)
Circom/snarkjs interpret JSON integers modulo the field prime, so negative integers cannot be range-checked directly as “signed ints”.
The Stage 3 circuits therefore use **shifted-input encoding** for robustness:

- Witness uses `x_shifted[i] = x_int[i] + maxAbsX` (so `x_shifted` is always non-negative)
- In-circuit, recover `x_int[i] = x_shifted[i] - maxAbsX` and apply defensive range checks

Reference bounds and constants come from `stage3_zk/artifacts/bounds.json`.

---

## 3. Bounds (for ZK Field Constraints)

Note: Any constraint counts, timings, or proof-size numbers in this note are rough planning estimates. The authoritative, reproducible measurements are captured by:
- `stage3_zk/reports/LATEST_REPRO_REPORT.md` (Complexity & Communication + Results)

From test set analysis (`stage3_zk/artifacts/bounds.json`):

- **max(|x_int|)**: 297,270,816 (~29 bits)
- **max(|w_int|)**: 122,130 (~17 bits)
- **max(|score_int|)**: 22,988,183,559 (~35 bits)

These bounds must fit within the ZK field (typically ~254 bits for BN254 curve, common in zkSNARKs).

**Verification:** All bounds < 2^36 (safe margin of ~218 bits for a 254-bit field).

### Bit Budget Analysis
Field size (BN254): 254 bits
Max score: 35 bits
Max intermediate: ~46 bits (x_int * w_int per feature)
Safety margin: 211 bits ✅

---

## 4. Circuit Levels (Progressive Complexity)

### Level 1: Inference Only
**Goal:** Prove `y_hat` is computed correctly from private `x` and public `w, b`.

**Public Inputs:**
- `w_int[104]`, `b_int` (model parameters)
- `Sx`, `Sw` (scales)
- `y_hat` (predicted label: 0 or 1)

**Private Witness:**
- `x_int[104]` (quantized feature vector; implemented as shifted witness `x_shifted[104]` in circuits)

**Constraints:**
score = Σ(w_int[i] * x_int[i]) + b_int // 104 multiplications + 103 additions
y_hat == (score >= 0) // sign check

**Challenge:** Implementing `>=` comparison in ZK (use range proofs or bit decomposition).

**Current measured complexity:** see `stage3_zk/reports/LATEST_REPRO_REPORT.md`.
Latest harness report: 3,831 constraints, proof JSON about 805 bytes, and per-sample prove steps around 1.0s in the CLI harness.

---

### Level 2: Inference + Group Aggregation
**Goal:** Prove `y_hat` + compute semantic group contributions `G[1..5]`.

**Additional Public Inputs:**
- (optional) `G[1..5]` — group contribution sums

**Additional Constraints:**
For each i in [0..103]:
c[i] = w_int[i] * x_int[i] // contribution per feature
abs_c[i] = |c[i]| // absolute value
gid = group_id[i] // constant from group_map.json
G[gid] += abs_c[i] // accumulate by group

**Challenge:** Implementing `abs()` in ZK:
- Introduce sign bit `z ∈ {0,1}`
- Enforce: `abs_c = (1 - 2z) * c` and `abs_c >= 0`

**Current measured complexity:** see `stage3_zk/reports/LATEST_REPRO_REPORT.md`.
Latest harness report: 17,684 constraints, proof JSON about 805 bytes, and per-sample prove steps around 1.3-1.5s in the CLI harness.

---

### Level 3: Full Top-3 Explainability (Option A)
**Goal:** Prove the 3 groups with highest contributions are `(g1, g2, g3)`.

**Public Inputs:**
- `w_int`, `b_int`, `y_hat` (from Level 1)
- `top3_groups = (g1, g2, g3)` where each `g ∈ {1,2,3,4,5}`

**Private Witness:**
- `x_int[104]` (implemented as shifted witness in circuits)
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

**Current measured complexity:** see `stage3_zk/reports/LATEST_REPRO_REPORT.md`.
Latest harness report: 18,719 constraints, proof JSON about 803 bytes, and per-sample prove steps around 1.3-1.5s in the CLI harness.

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

## 6. Current Benchmark Sources

Use these reports instead of the older planning estimates:

| Report | What to use it for |
|---|---|
| `stage3_zk/reports/LATEST_REPRO_REPORT.md` | Current circuit constraints, wires, public/private inputs, artifact sizes, proof sizes, and full build/witness/prove/verify status |
| `stage3_zk/reports/zk_scaling_benchmark.md` | Repeated Stage 3.3 prove/verify timing summary with p50/p95 |

Latest Stage 3.3 repeated benchmark summary:

| Step | Mean ms | p50 ms | p95 ms |
|---|---:|---:|---:|
| prepare_input | 77 | 70 | 109 |
| witness_smoke | 87 | 78 | 150 |
| prove | 1,532 | 1,484 | 1,847 |
| verify | 588 | 562 | 696 |

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

All ZK artifacts are frozen in `stage3_zk/artifacts/`:
- **feature_order.json** — 104 features in fixed order
- **group_map.json** — 5 semantic groups (Protocol, Application, ConnectionState, Ports, TrafficVolume)
- **model_public.json** — quantized weights (w_int[104], b_int, scales)
- **bounds.json** — field constraints (max values for safe arithmetic)

Test vectors in `stage3_zk/test_vectors/` for circuit validation:
- **test_sample_1.json** — True Positive attack (correctly detected)
- **test_sample_2.json** — True Negative normal traffic
- **test_sample_3.json** — False Negative attack (missed, for analysis)

---

## 10. Implementation Roadmap

### Phase 1: Circuit Development (Week 1-2)
- [x] Implement Stage 3.1 (inference only) in Circom (see `stage3_zk/circuits/inference_only/`)
- [x] Test with `test_sample_1.json`
- [x] Verify proof generation and verification work

### Phase 2: Group Aggregation (Week 3)
- [x] Implement Stage 3.2 semantic aggregation (see `stage3_zk/circuits/semantic_groups/`)
- [x] Test with all 3 test vectors

### Phase 3: Top-3 Constraint (Week 4)
- [x] Implement Stage 3.3 top-3 verification (see `stage3_zk/circuits/top3_explanation/`)
- [x] Add dominance + permutation constraints
- [x] End-to-end tests (including wrong-explanation rejection)

### Phase 4: Benchmarking (Week 5)
- [x] Run 100 proofs per level
- [x] Collect timing and size metrics
- [x] Reported in `stage3_zk/reports/FINAL_SUMMARY.md`

### Phase 5: Thesis Writing (Week 6+)
- [ ] Document results
- [ ] Compare with related work
- [ ] Discuss limitations and future work

---

**Last Updated:** February 3, 2026  
**Pipeline Version:** Stage 1 (processed_stratified_sample_23files_frac0.15) → Stage 2 (k=5 explainability) → Stage 3 (ZK circuits, n=104)  
**Status:** Artifacts ready ✅ | Circuits implemented ✅ | Benchmarks reported ✅
