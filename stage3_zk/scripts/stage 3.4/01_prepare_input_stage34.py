#!/usr/bin/env python
"""Stage 3.4: prepare inputs for Exact SHAP top-3 verification."""

from __future__ import annotations

import json
import os
import sys
from typing import Dict, List, Tuple


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STAGE3_ZK_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
ARTIFACTS_DIR = os.path.join(STAGE3_ZK_DIR, "artifacts")
TEST_VECTORS_DIR = os.path.join(STAGE3_ZK_DIR, "test_vectors")
OUTPUT_DIR = os.path.join(STAGE3_ZK_DIR, "circuits", "exact_shap_top3", "build")


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_exact_shap_groups(w_int: List[int], x_int: List[int], x_ref_int: List[int], group_map: Dict) -> List[int]:
    n_groups = int(group_map["n_groups"])
    group_ids = group_map["feature_index_to_group_id"]
    phi = [0] * n_groups
    for i, w_i in enumerate(w_int):
        gid = int(group_ids[i]) - 1
        phi[gid] += int(w_i) * (int(x_int[i]) - int(x_ref_int[i]))
    return phi


def compute_top3_and_others_by_abs(phi: List[int]) -> Tuple[List[int], List[int]]:
    groups = [(i + 1, abs(int(phi[i])), int(phi[i])) for i in range(len(phi))]
    groups_sorted = sorted(groups, key=lambda item: (-item[1], item[0]))
    top3_ids = [groups_sorted[i][0] for i in range(3)]
    other2_ids = [groups_sorted[i][0] for i in range(3, 5)]
    return top3_ids, other2_ids


def prepare_input(test_sample_id: int = 1) -> str:
    model = _read_json(os.path.join(ARTIFACTS_DIR, "model_public.json"))
    bounds = _read_json(os.path.join(ARTIFACTS_DIR, "bounds.json"))
    group_map = _read_json(os.path.join(ARTIFACTS_DIR, "group_map.json"))
    reference = _read_json(os.path.join(ARTIFACTS_DIR, "exact_shap_reference.json"))
    test_vec = _read_json(os.path.join(TEST_VECTORS_DIR, f"test_sample_{test_sample_id}.json"))

    max_abs_x = int(bounds["max_abs_x_int"])
    max_abs_w = int(bounds["max_abs_w_int"])
    B = 2**36

    w_int = [int(x) for x in model["w_int"]]
    b_int = int(model["b_int"])
    x_int = [int(x) for x in test_vec["x_int"]]
    x_ref_int = [int(x) for x in reference["x_ref_int"]]

    if len(x_int) != len(w_int) or len(x_ref_int) != len(w_int):
        raise ValueError(f"Dimension mismatch: x={len(x_int)}, x_ref={len(x_ref_int)}, w={len(w_int)}")

    score = sum(w_i * x_i for w_i, x_i in zip(w_int, x_int)) + b_int
    y_hat = 1 if score >= 0 else 0
    if int(test_vec["score_int"]) != score:
        raise ValueError(f"score mismatch against test vector: computed={score}, vector={test_vec['score_int']}")
    if int(test_vec["y_hat"]) != y_hat:
        raise ValueError(f"y_hat mismatch against test vector: computed={y_hat}, vector={test_vec['y_hat']}")
    if abs(score) > B:
        raise ValueError(f"score {score} exceeds circuit bound {B}")

    phi = compute_exact_shap_groups(w_int, x_int, x_ref_int, group_map)
    top3_ids, other2_ids = compute_top3_and_others_by_abs(phi)

    x_shifted = [x_i + max_abs_x for x_i in x_int]
    w_shifted = [w_i + max_abs_w for w_i in w_int]
    b_shifted = b_int + B

    if min(x_shifted) < 0 or max(x_shifted) > 2 * max_abs_x:
        raise ValueError("x_shifted outside configured bounds")
    if min(w_shifted) < 0 or max(w_shifted) > 2 * max_abs_w:
        raise ValueError("w_shifted outside configured bounds")
    if b_shifted < 0 or b_shifted > 2 * B:
        raise ValueError("b_shifted outside configured bounds")

    circuit_input = {
        "x_shifted": x_shifted,
        "w_shifted": w_shifted,
        "b_shifted": b_shifted,
        "y_hat": y_hat,
        "top3_ids": top3_ids,
        "other2_ids": other2_ids,
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f"input_sample_{test_sample_id}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(circuit_input, f, indent=2)

    group_names = group_map["groups"]
    print(f"OK: Prepared Stage 3.4 circuit input: {output_file}")
    print(f"   Sample: {test_vec.get('label', test_sample_id)}")
    print(f"   Score: {score}")
    print(f"   y_hat: {y_hat}")
    print("   Semantic-group Exact SHAP phi_int sorted by abs:")
    for rank, gid in enumerate(top3_ids + other2_ids, 1):
        marker = "*" if gid in top3_ids else " "
        value = phi[gid - 1]
        print(f"   {marker} [{rank}] Group {gid} {group_names[gid - 1]:20s}: phi={value:,}, abs={abs(value):,}")
    print(f"   Top-3 Exact SHAP groups (public): {top3_ids}")
    print(f"   Other 2 groups (private):        {other2_ids}")
    return output_file


if __name__ == "__main__":
    sample_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    prepare_input(sample_id)
