#!/usr/bin/env python
"""
Stage 3.3: Prepare input with top-3 explanation verification
"""

import json
import sys
import os

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Set base as stage3_zk directory
STAGE3_ZK_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
ARTIFACTS_DIR = os.path.join(STAGE3_ZK_DIR, "artifacts")
TEST_VECTORS_DIR = os.path.join(STAGE3_ZK_DIR, "test_vectors")
OUTPUT_DIR = os.path.join(STAGE3_ZK_DIR, "circuits", "top3_explanation", "build")

def compute_semantic_groups(w_int, x_int, group_map):
    """
    Compute semantic group contributions
    
    Returns:
        G: list of 5 group contributions
    """
    n = len(w_int)
    nGroups = group_map["n_groups"]
    group_ids = group_map["feature_index_to_group_id"]
    
    # Compute feature contributions
    c = [w_int[i] * x_int[i] for i in range(n)]
    
    # Compute absolute values
    a = [abs(c_i) for c_i in c]
    
    # Aggregate by group (1-indexed)
    G = [0] * nGroups
    for i in range(n):
        gid = group_ids[i] - 1  # Convert to 0-indexed
        G[gid] += a[i]
    
    return G

def compute_top3_and_others(G):
    """
    Compute top-3 group IDs and other 2 IDs
    
    Returns:
        top3_ids: list of 3 group IDs (1-indexed, sorted by G descending)
        other2_ids: list of 2 remaining group IDs (1-indexed)
    """
    # Create list of (group_id, G_value) pairs
    groups = [(i+1, G[i]) for i in range(len(G))]
    
    # Sort by G value descending
    groups_sorted = sorted(groups, key=lambda x: x[1], reverse=True)
    
    # Extract top-3 and others
    top3_ids = [groups_sorted[i][0] for i in range(3)]
    other2_ids = [groups_sorted[i][0] for i in range(3, 5)]
    
    return top3_ids, other2_ids

def check_bounds(score, B):
    """Verify score is within circuit bounds"""
    if abs(score) > B:
        print(f"❌ ERROR: Score {score} exceeds bound B={B}")
        print(f"   |score| = {abs(score)}, max allowed = {B}")
        return False
    return True

def prepare_input(test_sample_id=1):
    """
    Prepare circuit input from test vector with top-3 explanation
    """
    
    # Load model
    model_path = os.path.join(ARTIFACTS_DIR, "model_public.json")
    with open(model_path, "r") as f:
        model = json.load(f)
    
    # Load test vector
    test_file = os.path.join(TEST_VECTORS_DIR, f"test_sample_{test_sample_id}.json")
    with open(test_file, "r") as f:
        test_vec = json.load(f)
    
    # Load bounds
    bounds_path = os.path.join(ARTIFACTS_DIR, "bounds.json")
    with open(bounds_path, "r") as f:
        bounds = json.load(f)
    
    # Load group map
    group_map_path = os.path.join(ARTIFACTS_DIR, "group_map.json")
    with open(group_map_path, "r") as f:
        group_map = json.load(f)
    
    maxAbsX = bounds["max_abs_x_int"]
    maxAbsW = bounds["max_abs_w_int"]
    
    # Extract data
    w_int = model["w_int"]
    b_int = model["b_int"]
    x_int = test_vec["x_int"]
    y_hat = test_vec["y_hat"]
    score = test_vec["score_int"]
    
    # Verify dimensions
    n = len(w_int)
    assert len(x_int) == n, f"Dimension mismatch: x={len(x_int)}, w={n}"
    
    # Check bounds (B = 2^36)
    B = 2**36
    if not check_bounds(score, B):
        sys.exit(1)
    
    # Shift inputs to unsigned
    x_shifted = [x_i + maxAbsX for x_i in x_int]
    w_shifted = [w_i + maxAbsW for w_i in w_int]
    b_shifted = b_int + B
    
    # Verify shifted values are in valid range
    for i, xs in enumerate(x_shifted):
        if xs < 0 or xs > 2 * maxAbsX:
            print(f"❌ ERROR: x_shifted[{i}] = {xs} out of range [0, {2*maxAbsX}]")
            sys.exit(1)
    
    for i, ws in enumerate(w_shifted):
        if ws < 0 or ws > 2 * maxAbsW:
            print(f"❌ ERROR: w_shifted[{i}] = {ws} out of range [0, {2*maxAbsW}]")
            sys.exit(1)
    
    if b_shifted < 0 or b_shifted > 2 * B:
        print(f"❌ ERROR: b_shifted = {b_shifted} out of range [0, {2*B}]")
        sys.exit(1)
    
    # Compute semantic groups
    G = compute_semantic_groups(w_int, x_int, group_map)
    
    # Compute top-3 and other-2
    top3_ids, other2_ids = compute_top3_and_others(G)
    
    # Prepare circuit input
    circuit_input = {
        "x_shifted": x_shifted,      # Private witness (unsigned)
        "w_shifted": w_shifted,      # Public (unsigned)
        "b_shifted": b_shifted,      # Public (unsigned)
        "y_hat": y_hat,              # Public
        "top3_ids": top3_ids,        # Public (top-3 explanation)
        "other2_ids": other2_ids     # Private (remaining groups)
    }
    
    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f"input_sample_{test_sample_id}.json")
    
    with open(output_file, "w") as f:
        json.dump(circuit_input, f, indent=2)
    
    # Print summary
    group_names = group_map["groups"]
    
    print(f"✅ Prepared Stage 3.3 circuit input: {output_file}")
    print(f"   Sample: {test_vec['label']}")
    print(f"   Features: {n}")
    print(f"   Score: {score}")
    print(f"   y_hat: {y_hat} (0=normal, 1=attack)")
    print(f"   x_shifted range: [{min(x_shifted)}, {max(x_shifted)}]")
    print(f"   w_shifted range: [{min(w_shifted)}, {max(w_shifted)}]")
    print(f"   b_shifted: {b_shifted}")
    print(f"   Bound checks: OK")
    print(f"\n   Semantic Groups (sorted by contribution):")
    
    # Sort groups by value for display
    groups_display = [(i+1, group_names[i], G[i]) for i in range(len(G))]
    groups_display.sort(key=lambda x: x[2], reverse=True)
    
    for rank, (gid, name, val) in enumerate(groups_display, 1):
        marker = "⭐" if gid in top3_ids else "  "
        print(f"   {marker} [{rank}] Group {gid} {name:20s}: {val:,}")
    
    print(f"\n   Top-3 explanation (public): {top3_ids}")
    print(f"   Other 2 groups (private):   {other2_ids}")

if __name__ == "__main__":
    sample_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    prepare_input(sample_id)