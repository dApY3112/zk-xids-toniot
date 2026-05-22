#!/usr/bin/env python
"""Generate a Stage 3.4 witness for a prepared sample input."""

from __future__ import annotations

import os
import subprocess
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STAGE3_ZK_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
BUILD_DIR = os.path.join(STAGE3_ZK_DIR, "circuits", "exact_shap_top3", "build")


def witness_smoke(sample_id: int = 1) -> int:
    js_dir = os.path.join(BUILD_DIR, "exact_shap_top3_js")
    generator = os.path.join(js_dir, "generate_witness.js")
    wasm = os.path.join(js_dir, "exact_shap_top3.wasm")
    input_file = os.path.join(BUILD_DIR, f"input_sample_{sample_id}.json")
    witness = os.path.join(BUILD_DIR, f"witness_sample_{sample_id}.wtns")

    missing = [p for p in [generator, wasm, input_file] if not os.path.exists(p)]
    if missing:
        print("Missing required Stage 3.4 witness artifacts:")
        for path in missing:
            print(f"  - {path}")
        print("Compile circuit and prepare input first.")
        return 2

    proc = subprocess.run(
        ["node", generator, wasm, input_file, witness],
        cwd=STAGE3_ZK_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        print("FAIL: Stage 3.4 witness generation failed")
        print(proc.stderr[-1000:])
        return int(proc.returncode)

    print(f"PASS: Stage 3.4 witness generated: {witness}")
    return 0


if __name__ == "__main__":
    sample = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    raise SystemExit(witness_smoke(sample))
