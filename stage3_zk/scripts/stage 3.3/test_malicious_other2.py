#!/usr/bin/env python
"""
Security Test: Malicious other2 Witness Attack

Tests that prover cannot keep correct top3 but provide fake other2_ids
to bypass dominance constraints.
"""

import json
import subprocess
import os
import sys

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Set base as stage3_zk directory
STAGE3_ZK_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
ARTIFACTS_DIR = os.path.join(STAGE3_ZK_DIR, "artifacts")
TEST_VECTORS_DIR = os.path.join(STAGE3_ZK_DIR, "test_vectors")
CIRCUIT_DIR = os.path.join(STAGE3_ZK_DIR, "circuits", "top3_explanation")
BUILD_DIR = os.path.join(CIRCUIT_DIR, "build")
PROOFS_DIR = os.path.join(STAGE3_ZK_DIR, "outputs", "proofs")

def load_model():
    """Load model weights"""
    model_path = os.path.join(ARTIFACTS_DIR, "model_public.json")
    with open(model_path, "r") as f:
        return json.load(f)

def load_group_map():
    """Load semantic group mapping"""
    group_map_path = os.path.join(ARTIFACTS_DIR, "group_map.json")
    with open(group_map_path, "r") as f:
        return json.load(f)

def load_bounds():
    """Load bounds"""
    bounds_path = os.path.join(ARTIFACTS_DIR, "bounds.json")
    with open(bounds_path, "r") as f:
        return json.load(f)

def load_test_sample(sample_id):
    """Load test vector"""
    test_file = os.path.join(TEST_VECTORS_DIR, f"test_sample_{sample_id}.json")
    with open(test_file, "r") as f:
        return json.load(f)

def compute_semantic_groups(w_int, x_int, group_map):
    """Compute semantic group contributions"""
    n = len(w_int)
    nGroups = group_map["n_groups"]
    group_ids = group_map["feature_index_to_group_id"]
    
    c = [w_int[i] * x_int[i] for i in range(n)]
    a = [abs(c_i) for c_i in c]
    
    G = [0] * nGroups
    for i in range(n):
        gid = group_ids[i] - 1
        G[gid] += a[i]
    
    return G

def compute_correct_explanation(w_int, x_int, group_map):
    """Compute correct top-3 and other-2"""
    G = compute_semantic_groups(w_int, x_int, group_map)
    
    groups = [(i+1, G[i]) for i in range(len(G))]
    groups_sorted = sorted(groups, key=lambda x: x[1], reverse=True)
    
    top3_ids = [groups_sorted[i][0] for i in range(3)]
    other2_ids = [groups_sorted[i][0] for i in range(3, 5)]
    
    return top3_ids, other2_ids, G

def prepare_malicious_input(test_sample, top3_ids, malicious_other2, bounds, model):
    """Prepare circuit input with malicious other2"""
    maxAbsX = bounds["max_abs_x_int"]
    maxAbsW = bounds["max_abs_w_int"]
    B = 2**36
    
    w_int = model["w_int"]
    b_int = model["b_int"]
    x_int = test_sample["x_int"]
    y_hat = test_sample["y_hat"]
    
    # Shift inputs
    x_shifted = [x_i + maxAbsX for x_i in x_int]
    w_shifted = [w_i + maxAbsW for w_i in w_int]
    b_shifted = b_int + B
    
    circuit_input = {
        "x_shifted": x_shifted,
        "w_shifted": w_shifted,
        "b_shifted": b_shifted,
        "y_hat": y_hat,
        "top3_ids": top3_ids,
        "other2_ids": malicious_other2
    }
    
    return circuit_input

def generate_witness(input_data, test_name):
    """Generate witness and attempt proof"""
    # Save malicious input
    input_file = os.path.join(BUILD_DIR, f"malicious_input_{test_name}.json")
    with open(input_file, "w") as f:
        json.dump(input_data, f, indent=2)
    
    print(f"\n   Input saved: {input_file}")
    
    # Generate witness
    print(f"   Generating witness...")
    witness_file = os.path.join(BUILD_DIR, f"witness_{test_name}.wtns")
    
    wasm_file = os.path.join(BUILD_DIR, "top3_explanation_js", "top3_explanation.wasm")
    
    cmd = [
        "node",
        os.path.join(BUILD_DIR, "top3_explanation_js", "generate_witness.js"),
        wasm_file,
        input_file,
        witness_file
    ]
    
    result = subprocess.run(
        cmd,
        cwd=BUILD_DIR,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("   Witness generation failed (expected)")
        print(f"   Error: {result.stderr.strip()}")
        return False
    
    print("   Witness generation succeeded (unexpected)")
    
    # Try to generate proof
    print(f"   Attempting proof generation...")
    zkey_file = os.path.join(BUILD_DIR, "circuit_final.zkey")
    proof_file = os.path.join(BUILD_DIR, f"proof_{test_name}.json")
    public_file = os.path.join(BUILD_DIR, f"public_{test_name}.json")
    
    cmd = [
        "snarkjs", "groth16", "prove",
        zkey_file,
        witness_file,
        proof_file,
        public_file
    ]
    
    result = subprocess.run(
        cmd,
        cwd=BUILD_DIR,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("   Proof generation failed (expected)")
        print(f"   Error: {result.stderr.strip()}")
        return False
    
    print("   Proof generation succeeded (SECURITY VIOLATION)")
    return True

def main():
    print("=" * 70)
    print("Security Test: Malicious other2 Witness Attack")
    print("=" * 70)
    
    # Load data
    print("\n[1/4] Loading test data...")
    model = load_model()
    group_map = load_group_map()
    bounds = load_bounds()
    test_sample = load_test_sample(1)
    
    print(f"   Sample: {test_sample['label']}")
    print(f"   y_hat: {test_sample['y_hat']}")
    
    # Compute correct explanation
    print("\n[2/4] Computing correct explanation...")
    w_int = model["w_int"]
    x_int = test_sample["x_int"]
    
    top3_correct, other2_correct, G = compute_correct_explanation(w_int, x_int, group_map)
    
    group_names = group_map["groups"]
    print(f"\n   Correct top-3: {top3_correct}")
    for i, gid in enumerate(top3_correct):
        print(f"     [{i+1}] Group {gid} ({group_names[gid-1]}): {G[gid-1]:,}")
    
    print(f"\n   Correct other-2: {other2_correct}")
    for i, gid in enumerate(other2_correct):
        print(f"     [{i+1}] Group {gid} ({group_names[gid-1]}): {G[gid-1]:,}")
    
    # Test Case 1: Duplicate in other2
    print("\n[3/4] Test Case 1: Duplicate in other2")
    print("-" * 70)
    print(f"   Attack: Keep top3 correct, set other2 = [{other2_correct[0]}, {other2_correct[0]}]")
    print(f"   Expected: Fail at all-distinct constraint (line 246-258)")
    
    malicious_other2_dup = [other2_correct[0], other2_correct[0]]
    input_dup = prepare_malicious_input(test_sample, top3_correct, malicious_other2_dup, bounds, model)
    
    success_dup = generate_witness(input_dup, "duplicate")
    
    if success_dup:
        print("\n   SECURITY VIOLATION: Circuit accepted duplicate other2")
    else:
        print("\n   PASS: Circuit correctly rejected duplicate other2")
    
    # Test Case 2: Permutation violation (reuse group from top3)
    print("\n[4/4] Test Case 2: Permutation violation")
    print("-" * 70)
    print(f"   Attack: Keep top3 correct, set other2 = [{other2_correct[0]}, {top3_correct[0]}]")
    print(f"   Expected: Fail at permutation constraint (sum != 15 or sumsq != 55)")
    
    malicious_other2_perm = [other2_correct[0], top3_correct[0]]
    input_perm = prepare_malicious_input(test_sample, top3_correct, malicious_other2_perm, bounds, model)
    
    success_perm = generate_witness(input_perm, "permutation")
    
    if success_perm:
        print("\n   SECURITY VIOLATION: Circuit accepted permutation violation")
    else:
        print("\n   PASS: Circuit correctly rejected permutation violation")
    
    # Test Case 3: Out-of-range group ID
    print("\n[5/5] Test Case 3: Out-of-range group ID")
    print("-" * 70)
    print(f"   Attack: Keep top3 correct, set other2 = [6, {other2_correct[0]}]")
    print(f"   Expected: Fail at range check (group_id must be in {{1..5}})")
    
    malicious_other2_range = [6, other2_correct[0]]
    input_range = prepare_malicious_input(test_sample, top3_correct, malicious_other2_range, bounds, model)
    
    success_range = generate_witness(input_range, "out_of_range")
    
    if success_range:
        print("\n   SECURITY VIOLATION: Circuit accepted out-of-range group ID")
    else:
        print("\n   PASS: Circuit correctly rejected out-of-range group ID")
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    tests = [
        ("Duplicate other2", success_dup),
        ("Permutation violation", success_perm),
        ("Out-of-range ID", success_range)
    ]
    
    passed = sum(1 for _, success in tests if not success)
    total = len(tests)
    
    for test_name, success in tests:
        status = "FAIL (circuit vulnerable)" if success else "PASS"
        print(f"   {test_name:30s}: {status}")
    
    print(f"\n   Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n   ALL TESTS PASSED: Circuit defends against malicious witness attacks")
        print("\n   Thesis implication: Circuit enforces all-distinct, permutation,")
        print("   and range constraints, preventing prover from manipulating other2")
        print("   witness to bypass dominance checks.")
    else:
        print("\n   SECURITY ISSUES FOUND: Some attacks succeeded")
        print("   Review circuit constraints to fix vulnerabilities.")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()