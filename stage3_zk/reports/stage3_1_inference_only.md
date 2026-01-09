# Stage 3.1 Report — Inference-only ZK Proof (Groth16)

## 1) Goal
Prove rằng output phân loại `y_hat` là kết quả suy luận của Logistic Regression trên 104 features **mà không tiết lộ input features**.  
Verifier/SOC có thể kiểm chứng độc lập rằng prover dùng **đúng model đã công bố** và dự đoán là đúng theo rule `score >= 0`.

## 2) Artifacts (paths)
- Circuit: [circuits/inference_only/inference_only.circom](circuits/inference_only/inference_only.circom)
- Compiled outputs (R1CS/WASM/ZKEY/VK): [circuits/inference_only/build](circuits/inference_only/build)
- Model parameters (quantized): [artifacts/model_public.json](artifacts/model_public.json)
- Bounds: [artifacts/bounds.json](artifacts/bounds.json)
- Prepared circuit input example: [circuits/inference_only/build/input_sample_1.json](circuits/inference_only/build/input_sample_1.json)
- Proof & public signals (sample 1):
  - [outputs/proofs/proof_sample_1.json](outputs/proofs/proof_sample_1.json)
  - [outputs/proofs/public_sample_1.json](outputs/proofs/public_sample_1.json)
- Benchmarks:
  - WSL/CLI overhead benchmark: [outputs/proofs/benchmark_results.json](outputs/proofs/benchmark_results.json)
  - Optimized (Node API) benchmark: [outputs/proofs/benchmark_optimized.json](outputs/proofs/benchmark_optimized.json)

## 3) Circuit specification

### 3.1 Inputs/outputs (public/private)
Circuit in [circuits/inference_only/inference_only.circom](circuits/inference_only/inference_only.circom) uses:

- Private witness:
  - `x_shifted[104]` where `x_shifted[i] = x[i] + maxAbsX` (unsigned)
- Public signals (model binding + claimed output):
  - `w[104]`, `b`, `y_hat`

Main:
- `component main {public [w, b, y_hat]} = InferenceOnly(104, 37, 68719476736, 297270816);`

Note: Circuit files need updating - currently still use n=87 with old maxAbsX=67995696.

Why `x_shifted`:
- JSON negative integers get reduced mod BN254 field when interpreted by snarkjs/circom tooling, which breaks “signed range checks”.
- Shifting makes the input representable as an unsigned integer so the range check is meaningful and robust.

### 3.2 Decision rule
Compute integer score:
- `score = sum_i (w[i] * x[i]) + b`
- `y_hat = 1 if score >= 0 else 0`

### 3.3 Sign check (correct bit-width)
Use offset:
- `B = 2^36 = 68719476736`
- `score_offset = score + B`

If `score ∈ [-B, B-1]` then:
- `score_offset ∈ [0, 2B-1] = [0, 2^37 - 1]`

Therefore comparator must support 37-bit range:
- Circuit uses `LessThan(nBits)` with `nBits = 37`
- Checks `score_offset < B` to detect negative; then `pred = 1 - lt.out`

### 3.4 Defensive checks enforced in-circuit
1) Binary output:
- Enforce `y_hat ∈ {0,1}` via `y_hat * (y_hat - 1) == 0`

2) Input range (per feature):
- With `maxAbsX = 297270816` (from [artifacts/bounds.json](artifacts/bounds.json))
- Enforce `x_shifted[i] ∈ [0, 2*maxAbsX]` using:
  - `LessThan(30)` with bound `2*maxAbsX + 1` (inclusive upper bound)

3) Score bound:
- Enforce `0 <= score_offset < 2*B` using:
  - `LessThan(38)` with bound `2*B`

These checks prevent a prover from exploiting field wraparound / out-of-range values to satisfy the final predicate incorrectly.

### 3.5 Model binding rationale
If `w,b` were private witness, a malicious prover could pick a different model that makes any chosen `y_hat` valid.  
Making `w,b` public signals binds the proof to the published model parameters (the verifier checks the exact public vector).

Note: negative weights/bias appear “as large field elements” in `public_sample_*.json` (standard BN254 field representation).

## 4) Correctness evidence
- Proof verification succeeded using the generated VK and sample public signals:
  - `npx snarkjs groth16 verify ...` returns `OK!`
- In [outputs/proofs/public_sample_1.json](outputs/proofs/public_sample_1.json), the last element is `y_hat` (e.g., `"1"`).

## 5) Quantization / bounds (sanity)
From [artifacts/model_public.json](artifacts/model_public.json):
- `n = 104`, `Sx = 2^16`, `Sw = 2^12`
Circuit uses:
- `B = 2^36` and checks the score stays within this bound (via `score_offset` bound check).

Input preparation script [scripts/01_prepare_input.py](scripts/01_prepare_input.py):
- Creates `x_shifted`
- Checks `|score_int| <= B`
- Validates `x_shifted[i] ∈ [0, 2*maxAbsX]`

## 6) Performance (100 runs)
### 6.1 Optimized benchmark (authoritative cryptographic timings)
From [outputs/proofs/benchmark_optimized.json](outputs/proofs/benchmark_optimized.json):
- Proving (includes witness): mean **141.86 ms** (median 129 ms)
- Verification: mean **7.75 ms** (median 7 ms)

### 6.2 WSL/CLI baseline (includes process + filesystem overhead)
From [outputs/proofs/benchmark_results.json](outputs/proofs/benchmark_results.json):
- Proving: mean ≈ 2212 ms
- Verification: mean ≈ 1905 ms

Interpretation: CLI + WSL invocation overhead dominates; the optimized benchmark reflects the real proving/verifying cost more accurately.

## 7) How to run (Step 3.1)

### Build (compile + setup + vk)
From Windows PowerShell (repo root):
- `powershell -ExecutionPolicy Bypass -File scripts/02_build_circuit.ps1`

Notes:
- This script compiles with WSL circom at `/usr/local/bin/circom`, then runs `npx snarkjs` on Windows.

### Prepare input (sample k)
- `python scripts/01_prepare_input.py 1`

### Prove + verify
Using the provided WSL scripts:
- Prove: `wsl bash scripts/03_generate_proof.sh 1`
- Verify: `wsl bash scripts/04_verify_proof.sh 1`

### Benchmark (recommended)
- `node scripts/benchmark_optimized.js`