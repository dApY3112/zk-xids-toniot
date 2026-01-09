#!/usr/bin/env python
"""
Validate Stage 3.3 proof: check if public top-3 matches expected
"""

import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Set base as stage3_zk directory
STAGE3_ZK_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
ARTIFACTS_DIR = os.path.join(STAGE3_ZK_DIR, "artifacts")
TEST_VECTORS_DIR = os.path.join(STAGE3_ZK_DIR, "test_vectors")
OUTPUTS_DIR = os.path.join(STAGE3_ZK_DIR, "outputs", "proofs")

def compute_expected_top3(test_sample_id):
    """Compute expected top-3 from test vector"""
    
    # Load model
    with open(os.path.join(ARTIFACTS_DIR, "model_public.json"), "r") as f:
        model = json.load(f)
    
    # Load test vector
    with open(os.path.join(TEST_VECTORS_DIR, f"test_sample_{test_sample_id}.json"), "r") as f:
        test_vec = json.load(f)
    
    # Load group map
    with open(os.path.join(ARTIFACTS_DIR, "group_map.json"), "r") as f:
        group_map = json.load(f)
    
    w_int = model["w_int"]
    x_int = test_vec["x_int"]
    group_ids = group_map["feature_index_to_group_id"]
    
    # Compute contributions
    c = [w_int[i] * x_int[i] for i in range(len(w_int))]
    a = [abs(c_i) for c_i in c]
    
    # Aggregate by group
    G = [0] * 5
    for i in range(len(a)):
        gid = group_ids[i] - 1
        G[gid] += a[i]
    
    # Get top-3
    groups = [(i+1, G[i]) for i in range(5)]
    groups.sort(key=lambda x: x[1], reverse=True)
    top3_ids = [groups[i][0] for i in range(3)]
    
    return top3_ids, G, test_vec, group_map

def validate_proof(test_sample_id):
    """Validate proof public signals match expected top-3"""
    
    print(f"Validating Stage 3.3 proof for sample {test_sample_id}...")
    
    # Compute expected
    expected_top3, G, test_vec, group_map = compute_expected_top3(test_sample_id)
    
    # Load public signals
    public_file = os.path.join(OUTPUTS_DIR, f"public_stage33_sample_{test_sample_id}.json")
    with open(public_file, "r") as f:
        public_signals = json.load(f)
    
    # Extract top3_ids from public signals (last 3 elements)
    actual_top3 = [int(x) for x in public_signals[-3:]]
    
    # Compare
    print(f"\n{'Expected Top-3:':<20} {expected_top3}")
    print(f"{'Actual Top-3:':<20} {actual_top3}")
    
    group_names = group_map["groups"]
    
    print(f"\n{'Rank':<6} {'Group ID':<10} {'Name':<25} {'Contribution':<15}")
    print("=" * 70)
    
    # Show all groups sorted
    groups_display = [(i+1, group_names[i], G[i]) for i in range(5)]
    groups_display.sort(key=lambda x: x[2], reverse=True)
    
    for rank, (gid, name, val) in enumerate(groups_display, 1):
        marker = "✅" if gid in actual_top3 else "  "
        print(f"{marker} {rank:<5} {gid:<10} {name:<25} {val:,}")
    
    print("=" * 70)
    print(f"Sample: {test_vec['label']}")
    print(f"y_hat:  {test_vec['y_hat']} (0=normal, 1=attack)")
    
    if expected_top3 == actual_top3:
        print("\n✅ VALIDATION PASSED: Top-3 explanation matches!")
        return 0
    else:
        print("\n❌ VALIDATION FAILED: Top-3 mismatch!")
        return 1

if __name__ == "__main__":
    sample_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    sys.exit(validate_proof(sample_id))