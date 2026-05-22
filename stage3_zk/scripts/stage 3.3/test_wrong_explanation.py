#!/usr/bin/env python
"""
Test Stage 3.3: Verify circuit rejects wrong top-3 explanation
"""

import json
import sys
import os
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Set base as stage3_zk directory
STAGE3_ZK_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
ARTIFACTS_DIR = os.path.join(STAGE3_ZK_DIR, "artifacts")
TEST_VECTORS_DIR = os.path.join(STAGE3_ZK_DIR, "test_vectors")
OUTPUT_DIR = os.path.join(STAGE3_ZK_DIR, "circuits", "top3_explanation", "build")

def load_correct_input(test_sample_id=1):
    """Load the correct input"""
    input_file = os.path.join(OUTPUT_DIR, f"input_sample_{test_sample_id}.json")
    with open(input_file, "r") as f:
        return json.load(f)

def create_wrong_explanation(correct_input):
    """Create input with WRONG top-3 (swap with one from other2)"""
    wrong_input = correct_input.copy()
    
    # Swap top3[2] with other2[0] - this should make proof fail
    print(f"\nOriginal top3: {correct_input['top3_ids']}")
    print(f"Original other2: {correct_input['other2_ids']}")
    
    wrong_top3 = correct_input['top3_ids'].copy()
    wrong_other2 = correct_input['other2_ids'].copy()
    
    # Swap
    wrong_top3[2] = correct_input['other2_ids'][0]
    wrong_other2[0] = correct_input['top3_ids'][2]
    
    wrong_input['top3_ids'] = wrong_top3
    wrong_input['other2_ids'] = wrong_other2
    
    print(f"\nWRONG top3: {wrong_top3}")
    print(f"WRONG other2: {wrong_other2}")
    
    return wrong_input

def test_wrong_explanation(test_sample_id=1):
    """Test that circuit rejects wrong explanation"""
    
    print("=" * 60)
    print("TESTING WRONG EXPLANATION (Should FAIL)")
    print("=" * 60)
    
    # Load correct input
    correct_input = load_correct_input(test_sample_id)
    
    # Create wrong input
    wrong_input = create_wrong_explanation(correct_input)
    
    # Save wrong input
    wrong_file = os.path.join(OUTPUT_DIR, f"input_sample_{test_sample_id}_WRONG.json")
    with open(wrong_file, "w") as f:
        json.dump(wrong_input, f, indent=2)
    
    print(f"\nOK: Created wrong input: {wrong_file}")
    
    # Try to generate witness (should fail)
    print("\nAttempting to generate witness with wrong explanation...")
    
    wasm = os.path.join(OUTPUT_DIR, "top3_explanation_js", "top3_explanation.wasm")
    witness_out = os.path.join(OUTPUT_DIR, "witness_WRONG.wtns")
    
    try:
        result = subprocess.run(
            ["node", os.path.join(OUTPUT_DIR, "top3_explanation_js", "generate_witness.js"),
             wasm, wrong_file, witness_out],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print("\nPASS: Witness generation failed as expected")
            print("Circuit correctly rejected wrong explanation")
            print(f"\nError message:\n{result.stderr[:500]}")
            return 0
        else:
            print("\nFAIL: Witness generation succeeded (should have failed)")
            print("Circuit accepted wrong explanation - BUG IN CIRCUIT")
            return 1
            
    except subprocess.TimeoutExpired:
        print("\nFAIL: Witness generation timed out")
        return 1
    except Exception as e:
        print(f"\nFAIL: Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sample_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    sys.exit(test_wrong_explanation(sample_id))