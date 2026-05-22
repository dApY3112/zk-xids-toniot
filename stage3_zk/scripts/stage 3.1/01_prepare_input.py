#!/usr/bin/env python
"""
Convert test_sample_X.json -> circuit input format with x_shifted (unsigned)
"""

import json
import numpy as np
import sys
import os

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Set base as stage3_zk directory
STAGE3_ZK_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
ARTIFACTS_DIR = os.path.join(STAGE3_ZK_DIR, "artifacts")
TEST_VECTORS_DIR = os.path.join(STAGE3_ZK_DIR, "test_vectors")
OUTPUT_DIR = os.path.join(STAGE3_ZK_DIR, "circuits", "inference_only", "build")

def check_bounds(score, B):
    """Verify score is within circuit bounds"""
    if abs(score) > B:
        print(f"ERROR: Score {score} exceeds bound B={B}")
        print(f"   |score| = {abs(score)}, max allowed = {B}")
        return False
    return True

def prepare_input(test_sample_id=1):
    """
    Prepare circuit input from test vector
    
    Args:
        test_sample_id: 1, 2, or 3
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
    
    maxAbsX = bounds["max_abs_x_int"]
    
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
    
    # Convert x to x_shifted (unsigned): x_shifted[i] = x[i] + maxAbsX
    x_shifted = [x_i + maxAbsX for x_i in x_int]
    
    # Verify x_shifted is in valid range [0, 2*maxAbsX]
    for i, xs in enumerate(x_shifted):
        if xs < 0 or xs > 2 * maxAbsX:
            print(f"ERROR: x_shifted[{i}] = {xs} out of range [0, {2*maxAbsX}]")
            sys.exit(1)
    
    # Prepare circuit input
    circuit_input = {
        "x_shifted": x_shifted,  # Private witness (unsigned)
        "w": w_int,              # Public
        "b": b_int,              # Public
        "y_hat": y_hat           # Public
    }
    
    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f"input_sample_{test_sample_id}.json")
    
    with open(output_file, "w") as f:
        json.dump(circuit_input, f, indent=2)
    
    # Print summary
    print(f"OK: Prepared circuit input: {output_file}")
    print(f"   Sample: {test_vec['label']}")
    print(f"   Features: {n}")
    print(f"   Score: {score}")
    print(f"   y_hat: {y_hat} (0=normal, 1=attack)")
    print(f"   x_shifted range: [{min(x_shifted)}, {max(x_shifted)}]")
    print(f"   Bound check: OK (|{score}| < {B})")

if __name__ == "__main__":
    sample_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    prepare_input(sample_id)