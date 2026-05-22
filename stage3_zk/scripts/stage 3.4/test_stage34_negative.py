#!/usr/bin/env python
"""Negative witness tests for Stage 3.4 Exact SHAP top-3 verification."""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from typing import Dict, Tuple


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STAGE3_ZK_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BUILD_DIR = os.path.join(STAGE3_ZK_DIR, "circuits", "exact_shap_top3", "build")


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, payload) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _make_cases(base: Dict) -> Dict[str, Dict]:
    cases: Dict[str, Dict] = {}

    wrong_y = copy.deepcopy(base)
    wrong_y["y_hat"] = 1 - int(base["y_hat"])
    cases["wrong_y_hat"] = wrong_y

    wrong_top3 = copy.deepcopy(base)
    wrong_top3["top3_ids"] = list(base["top3_ids"])
    wrong_top3["other2_ids"] = list(base["other2_ids"])
    wrong_top3["top3_ids"][2], wrong_top3["other2_ids"][0] = wrong_top3["other2_ids"][0], wrong_top3["top3_ids"][2]
    cases["wrong_top3"] = wrong_top3

    duplicate = copy.deepcopy(base)
    duplicate["other2_ids"] = list(base["other2_ids"])
    duplicate["other2_ids"][0] = int(base["top3_ids"][0])
    cases["duplicate_group_id"] = duplicate

    out_of_range = copy.deepcopy(base)
    out_of_range["other2_ids"] = list(base["other2_ids"])
    out_of_range["other2_ids"][0] = 6
    cases["out_of_range_group_id"] = out_of_range

    malicious_other2 = copy.deepcopy(base)
    malicious_other2["other2_ids"] = list(reversed(base["top3_ids"][:2]))
    cases["malicious_other2_reuses_top"] = malicious_other2

    bad_private_range = copy.deepcopy(base)
    bad_private_range["x_shifted"] = list(base["x_shifted"])
    bad_private_range["x_shifted"][0] = -1
    cases["private_input_range_violation"] = bad_private_range

    return cases


def _run_witness(input_path: str, witness_path: str) -> Tuple[int, str]:
    js_dir = os.path.join(BUILD_DIR, "exact_shap_top3_js")
    generator = os.path.join(js_dir, "generate_witness.js")
    wasm = os.path.join(js_dir, "exact_shap_top3.wasm")
    missing = [p for p in [generator, wasm] if not os.path.exists(p)]
    if missing:
        return 2, "Missing compiled Stage 3.4 WASM/generator. Compile circuit first."

    proc = subprocess.run(
        ["node", generator, wasm, input_path, witness_path],
        cwd=STAGE3_ZK_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return int(proc.returncode), (proc.stderr or proc.stdout or "")


def run_negative_tests(sample_id: int = 1) -> int:
    base_path = os.path.join(BUILD_DIR, f"input_sample_{sample_id}.json")
    if not os.path.exists(base_path):
        print(f"Missing base input: {base_path}")
        print("Run 01_prepare_input_stage34.py first.")
        return 2

    base = _read_json(base_path)
    cases = _make_cases(base)
    failures = []

    for name, payload in cases.items():
        input_path = os.path.join(BUILD_DIR, f"input_sample_{sample_id}_{name}.json")
        witness_path = os.path.join(BUILD_DIR, f"witness_sample_{sample_id}_{name}.wtns")
        _write_json(input_path, payload)
        rc, output = _run_witness(input_path, witness_path)
        if rc == 2:
            print(output)
            return 2
        if rc == 0:
            print(f"FAIL: negative case unexpectedly generated witness: {name}")
            failures.append(name)
        else:
            print(f"PASS: negative case rejected as expected: {name}")

    if failures:
        print("Stage 3.4 negative test failures: " + ", ".join(failures))
        return 1

    print("PASS: all Stage 3.4 negative witness tests rejected invalid inputs")
    return 0


if __name__ == "__main__":
    sample = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    raise SystemExit(run_negative_tests(sample))
