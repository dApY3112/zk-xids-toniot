#!/usr/bin/env python
"""
Diversity/Sensitivity Test for Stage 3.3
Tests that top-3 explanations vary across different samples
"""

import json
import numpy as np
from collections import Counter
import os
import sys

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Set base as stage3_zk directory
STAGE3_ZK_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
ARTIFACTS_DIR = os.path.join(STAGE3_ZK_DIR, "artifacts")
TEST_VECTORS_DIR = os.path.join(STAGE3_ZK_DIR, "test_vectors")
OUTPUTS_DIR = os.path.join(STAGE3_ZK_DIR, "outputs")

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

def load_test_indices():
    """Load test set indices"""
    test_idx_path = os.path.join(OUTPUTS_DIR, "splits", "test_idx.npy")
    return np.load(test_idx_path)

def load_test_data():
    """Load X_test and y_test"""
    X_test = np.load(os.path.join(OUTPUTS_DIR, "processed", "X_test.npy"))
    y_test = np.load(os.path.join(OUTPUTS_DIR, "processed", "y_test.npy"))
    return X_test, y_test

def quantize_input(x_float, Sx=2**16):
    """Quantize float input to integer"""
    return np.round(x_float * Sx).astype(np.int64)

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

def compute_top3(w_int, x_int, group_map):
    """
    Compute top-3 group IDs
    
    Returns:
        top3_ids: list of 3 group IDs (1-indexed, sorted by G descending)
    """
    G = compute_semantic_groups(w_int, x_int, group_map)
    
    # Create list of (group_id, G_value) pairs
    groups = [(i+1, G[i]) for i in range(len(G))]
    
    # Sort by G value descending
    groups_sorted = sorted(groups, key=lambda x: x[1], reverse=True)
    
    # Extract top-3
    top3_ids = [groups_sorted[i][0] for i in range(3)]
    
    return top3_ids, G

def main():
    print("=" * 60)
    print("Stage 3.3: Diversity/Sensitivity Test")
    print("=" * 60)
    
    # Load data
    print("\n[1/5] Loading model and data...")
    model = load_model()
    group_map = load_group_map()
    X_test, y_test = load_test_data()
    
    w_int = model["w_int"]
    
    print(f"   Model: {len(w_int)} features")
    print(f"   Test set: {len(X_test)} samples")
    print(f"   Attack samples: {sum(y_test == 1)}")
    print(f"   Normal samples: {sum(y_test == 0)}")
    
    # Select 50 samples (25 attack + 25 normal)
    print("\n[2/5] Selecting 50 samples...")
    attack_indices = np.where(y_test == 1)[0][:25]
    normal_indices = np.where(y_test == 0)[0][:25]
    
    print(f"   Attack samples: {len(attack_indices)}")
    print(f"   Normal samples: {len(normal_indices)}")
    
    # Compute top-3 for each sample
    print("\n[3/5] Computing top-3 explanations...")
    
    top3_attack = []
    G_attack = []
    for idx in attack_indices:
        x_float = X_test[idx]
        x_int = quantize_input(x_float)
        top3, G = compute_top3(w_int, x_int, group_map)
        top3_attack.append(tuple(top3))
        G_attack.append(G)
    
    top3_normal = []
    G_normal = []
    for idx in normal_indices:
        x_float = X_test[idx]
        x_int = quantize_input(x_float)
        top3, G = compute_top3(w_int, x_int, group_map)
        top3_normal.append(tuple(top3))
        G_normal.append(G)
    
    # Statistics
    print("\n[4/5] Analyzing diversity...")
    print("\n" + "=" * 60)
    print("RESULTS: Top-3 Pattern Diversity")
    print("=" * 60)
    
    # Unique patterns
    unique_attack = len(set(top3_attack))
    unique_normal = len(set(top3_normal))
    
    print(f"\nUnique top-3 patterns:")
    print(f"  Attack class:  {unique_attack}/25 ({unique_attack/25*100:.1f}%)")
    print(f"  Normal class:  {unique_normal}/25 ({unique_normal/25*100:.1f}%)")
    
    # Most frequent patterns
    print(f"\n--- Top-3 Attack Patterns ---")
    attack_counter = Counter(top3_attack)
    group_names = group_map["groups"]
    
    for pattern, count in attack_counter.most_common(5):
        pct = count / len(top3_attack) * 100
        pattern_str = " → ".join([group_names[gid-1] for gid in pattern])
        print(f"  {pattern}  ({pct:5.1f}%)  {pattern_str}")
    
    print(f"\n--- Top-3 Normal Patterns ---")
    normal_counter = Counter(top3_normal)
    
    for pattern, count in normal_counter.most_common(5):
        pct = count / len(top3_normal) * 100
        pattern_str = " → ".join([group_names[gid-1] for gid in pattern])
        print(f"  {pattern}  ({pct:5.1f}%)  {pattern_str}")
    
    # Jaccard similarity
    print("\n" + "=" * 60)
    print("Class Separation Analysis")
    print("=" * 60)
    
    attack_set = set(top3_attack)
    normal_set = set(top3_normal)
    
    intersection = attack_set & normal_set
    union = attack_set | normal_set
    jaccard = len(intersection) / len(union) if len(union) > 0 else 0
    
    print(f"\nJaccard similarity: {jaccard:.3f}")
    print(f"  (0 = completely different, 1 = identical)")
    
    if jaccard < 0.5:
        print(f"  ✅ LOW similarity → Attack/Normal have DISTINCT profiles")
    else:
        print(f"  ⚠️  HIGH similarity → Patterns overlap significantly")
    
    print(f"\nShared patterns: {len(intersection)}/{len(union)}")
    print(f"Attack-only patterns: {len(attack_set - normal_set)}")
    print(f"Normal-only patterns: {len(normal_set - attack_set)}")
    
    # Top-1 group frequency
    print("\n" + "=" * 60)
    print("Top-1 Group Frequency (Most Important Feature)")
    print("=" * 60)
    
    top1_attack = [pattern[0] for pattern in top3_attack]
    top1_normal = [pattern[0] for pattern in top3_normal]
    
    top1_attack_counter = Counter(top1_attack)
    top1_normal_counter = Counter(top1_normal)
    
    print(f"\n--- Attack Class ---")
    for gid, count in top1_attack_counter.most_common():
        pct = count / len(top1_attack) * 100
        print(f"  Group {gid} ({group_names[gid-1]:20s}): {count}/25 ({pct:5.1f}%)")
    
    print(f"\n--- Normal Class ---")
    for gid, count in top1_normal_counter.most_common():
        pct = count / len(top1_normal) * 100
        print(f"  Group {gid} ({group_names[gid-1]:20s}): {count}/25 ({pct:5.1f}%)")
    
    # Average group contributions
    print("\n" + "=" * 60)
    print("Average Group Contributions")
    print("=" * 60)
    
    G_attack_avg = np.mean(G_attack, axis=0)
    G_normal_avg = np.mean(G_normal, axis=0)
    
    print(f"\n{'Group':<25} {'Attack (avg)':<20} {'Normal (avg)':<20}")
    print("-" * 65)
    for i in range(5):
        gname = group_names[i]
        print(f"{gname:<25} {G_attack_avg[i]:>15,.0f}  {G_normal_avg[i]:>15,.0f}")
    
    # Save results
    print("\n[5/5] Saving results...")
    
    # Convert tuple keys to strings for JSON serialization
    attack_patterns_dict = {str(k): v for k, v in attack_counter.most_common(5)}
    normal_patterns_dict = {str(k): v for k, v in normal_counter.most_common(5)}
    
    results = {
        "n_samples": {
            "attack": len(attack_indices),
            "normal": len(normal_indices)
        },
        "unique_patterns": {
            "attack": unique_attack,
            "normal": unique_normal
        },
        "top_patterns": {
            "attack": attack_patterns_dict,
            "normal": normal_patterns_dict
        },
        "jaccard_similarity": jaccard,
        "top1_frequency": {
            "attack": dict(top1_attack_counter),
            "normal": dict(top1_normal_counter)
        },
        "avg_group_contributions": {
            "attack": G_attack_avg.tolist(),
            "normal": G_normal_avg.tolist()
        }
    }
    
    output_file = os.path.join(BASE_DIR, "outputs", "diversity_analysis.json")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"   Saved: {output_file}")
    
    print("\n" + "=" * 60)
    print("✅ Diversity test complete!")
    print("=" * 60)
    
    # Thesis implications
    print("\n📊 THESIS IMPLICATIONS:")
    if unique_attack + unique_normal >= 8:
        print("  ✅ High diversity → Explanations are INPUT-SENSITIVE")
    else:
        print("  ⚠️  Low diversity → May need more samples or feature engineering")
    
    if jaccard < 0.5:
        print("  ✅ Low Jaccard → Attack/Normal have DISTINCT patterns")
    else:
        print("  ℹ️  High Jaccard → Similar patterns (may be dataset-specific)")
    
    print("\n  Use these results in Section 7.1.2 of thesis report!")

if __name__ == "__main__":
    main()